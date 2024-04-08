# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


import logging
import importlib.util
import copy
from elmer_helpers import read_result_smatrix, produce_sif_files
from run_helpers import _run_elmer_solver

from scipy.signal import find_peaks, peak_prominences, peak_widths
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt

has_polyrat = importlib.util.find_spec("polyrat") is not None
if has_polyrat:
    from polyrat import StabilizedSKRationalApproximation as SK_fit


def rational_fit(f, s_data, num_order, denom_order):
    """
    Args:
        f        (np.array): Independent variable of the fit (frequency)
        s_data   (np.array): Dependent variable of the fit (s matrix component)
        min_num_order (int): Order of the numerator of the fitted rational function
        max_num_order (int): Order of the denominator of the fitted rational function

    Returns:
        residual (float): redisual of the fit
        func (float -> float): function of the fit

    """
    if has_polyrat:
        fit_obj = SK_fit(num_order, denom_order, verbose=False, maxiter=50, xtol=1e-9)
        fit_obj.fit(f.reshape(-1, 1), s_data)

        def func(x):
            return fit_obj(x.reshape(-1, 1))

        residual = np.linalg.norm(func(f.reshape(-1, 1)) - s_data)
    else:

        def _rational_fun(x, coefs_num, coefs_denom):
            return np.polyval(coefs_num, x) / np.polyval(coefs_denom, x)

        def _create_rational_fun_for_fit(num_order_cl, denom_order_cl):
            def fit_func(*args):
                return _rational_fun(
                    args[0],
                    [*args[1 : (num_order_cl + 2)]],
                    [*args[(num_order_cl + 2) : (num_order_cl + denom_order_cl + 2)]] + [1.0],
                )

            return fit_func

        initial_guess = tuple((num_order + denom_order + 1) * [1.0])
        mesg = ""
        try:
            fit_func = _create_rational_fun_for_fit(num_order, denom_order)
            popt, _, infodict, mesg, _ = curve_fit(fit_func, f, s_data, p0=initial_guess, full_output=True)
            residual = np.linalg.norm(infodict["fvec"])

            def func(x):
                return fit_func(x, *popt)

        except RuntimeError:
            logging.warning(
                "Least squares fit failed in interpolated frequency sweep, "
                f"rational order ({num_order}, {denom_order})"
            )
            logging.warning(mesg)
            residual = float("inf")

            def func(x):
                return x

    return (residual, func)


def sweep_orders_and_fit(f_all, s_all, min_num_order=0, max_num_order=10, min_denom_order=2, max_denom_order=20):
    """
    Args:
        f_all     (np.array): All frequencies calculated so far
        s_all     (np.array): Single S-matrix component at all of the frequencies
        min_num_order  (int): minimum order of the numerator of the fitted rational function
        max_num_order  (int): maximum order of the numerator of the fitted rational function
        min_denom_order (int): minimum order of the denominator of the fitted rational function
        max_denom_order (int): maximum order of the denominator of the fitted rational function

    Returns:
        min_func (float -> float): function of the best fit
        orders (tuple): orders of the numerator and denominator for the best fit
    """
    min_residual = float("inf")
    min_func = None
    orders = (0, 0)
    for num_order in range(min_num_order, max_num_order + 1):
        effective_len = len(f_all) if len(f_all) < 10 else len(f_all) // 2
        cur_max_denom_order = min(effective_len - num_order - 1, max_denom_order + 1)
        for denom_order in range(min_denom_order, cur_max_denom_order):
            residual, func = rational_fit(f_all, s_all, num_order, denom_order)
            if residual < min_residual:
                min_residual = residual
                min_func = func
                orders = (num_order, denom_order)
    return min_func, orders


def interpolating_frequency_sweep(
    json_data, exec_path_override=None, fit_index=1, fit_magnitude=False, max_iter=20, plot_results=True
):
    """
    Run interpolated frequency sweep

    Args:
        json_data             (dict): Simulation data loaded from the .json in simulation tmp folder
        n_parallel_simulations (int): Number of parallel simulations
        n_processes            (int): Number of dependent processes for each simulation
        n_threads              (int): Number of threads to be used with elmer
        exec_path_override    (Path): Working directory from where the simulations are run
                                      (usually KQCircuits/tmp/sim_name)
        fit_index              (int): Smatrix component S(0, fit_index) used for fitting and interpolating
                                      Note that indexing starts from 0, e.g fitindex 0 is S11 and 1 is S12
        fit_magnitude         (bool): If true fits the magnitude component of S(0, fit_index),
                                      If False fits real and imaginary parts separately.
                                      For now Only applies to intermediate steps. The final result fitting is
                                      done separately for real and im parts
        max_iter               (int):  Maximum number of interpolation steps with new simulations
        plot_results          (bool): If True saves plots for intermediate and final S matrix fitting
                                      results as png files

    """
    if not has_polyrat:
        logging.warning(
            "Rational fit using scipy.curve_fit is extremely unreliable." " Consider installing polyrat library"
        )

    if json_data["workflow"]["_parallelization_level"] == "elmer":
        n_parallel_simulations = json_data["workflow"].get("n_workers", 1)
    else:
        n_parallel_simulations = 1

    n_processes = json_data["workflow"].get("elmer_n_processes", 1)
    n_threads = json_data["workflow"].get("elmer_n_threads", 1)

    if plot_results:
        image_folder = exec_path_override.joinpath("s_matrix_plots")
        image_folder.mkdir(parents=True, exist_ok=True)

    json_freqs = np.array(json_data["frequency"])
    start_f = min(json_freqs)
    end_f = max(json_freqs)
    if start_f == end_f:
        raise ValueError(f"Cannot do interpolating sweep as only a single frequency was given (f={json_freqs})")

    frequency_batch = json_data["frequency_batch"]
    max_delta_s = json_data["max_delta_s"]
    simname = json_data["name"]

    def mag_from_components(re_arr, im_arr):
        return np.sqrt(np.power(re_arr, 2) + np.power(im_arr, 2))

    def _sample_on_slope(func, f_sampled, s_sampled, batch_size, max_p_factor=5, nevals=10000):
        """
        Args:
            func (float -> float): fitted magnitude of S-matrix component
            f_sampled (np.array): list of frequencies sampled on previous iterations
            s_sampled (np.array): list of S-matrix magnitudes used for the sampling
            batch_size (int): how many frequencies are sampled
            max_p_factor (float): How many times more likely to sample the point with highest gradient
                                  vs the point with lowest gradient.
            nevals (int): Number of evaluations of func for evaluation of gradients and peak finding

        Returns:
            list of frequencies for the next batch of simulations

        Samples:
        1. The most prominent peak from the previous iteration fit
        2. The most prominent peak from all simulation S-matrix data so far
        3. Rest based on the slope of the fitted response. The higher the abs(slope) the
           higher the probability of choosing that point

        P_sample
            ^
            |                  _________________________________
        max_p_factor          /
            |              --
            |            /
            |        ---
            1 ------/
            |
            |-------------------------------------------------> |df/dx|

        """
        f_start = f_sampled[0]
        f_end = f_sampled[-1]
        x = np.linspace(f_start, f_end, nevals)
        fx = func(x)
        choices = np.zeros(batch_size)

        def find_all_prominences(data):
            """
            find peaks and dips from data and sort them by prominence.
            """

            def find_and_filter_prominences(data):
                """
                Find peaks and their prominances in data and filter out the ones
                which have width larger than half of the data. This prevents us from
                sampling the top of a parabola on every iteration
                """
                data_width = len(data)
                peaks, _ = find_peaks(data)
                prominences = peak_prominences(data, peaks)
                widths = peak_widths(data, peaks, rel_height=0.1, prominence_data=prominences)[0]
                peaks = peaks[widths < data_width / 10]
                prominences = prominences[0]
                prominences = prominences[widths < data_width / 10]
                return (peaks, prominences)

            peaks_p, prominences_p = find_and_filter_prominences(data)
            peaks_m, prominences_m = find_and_filter_prominences(-data)

            peaks_all = np.concatenate((peaks_p, peaks_m))
            prominences_all = np.concatenate((prominences_p, prominences_m))
            sort_index = prominences_all.argsort()
            peaks_all, prominences_all = peaks_all[sort_index], prominences_all[sort_index]
            return (peaks_all, prominences_all)

        fit_inds, _ = find_all_prominences(fx)
        data_inds, _ = find_all_prominences(s_sampled)
        sample_ind = 0
        if len(fit_inds) != 0:
            choices[sample_ind] = x[fit_inds[-1]]
            sample_ind += 1

        if sample_ind < batch_size and len(data_inds) != 0:
            choices[sample_ind] = f_sampled[data_inds[-1]]
            sample_ind += 1

        if sample_ind < batch_size:
            abs_slopes = np.abs(np.gradient(fx))
            # scale the gradients t interval [0, 1]
            abs_slopes = abs_slopes / np.max(abs_slopes)
            # map the abs gradients [0, 1] to weights [1, max_p_factor]
            weights = 1 + max_p_factor * abs_slopes
            # normalize probabilities
            weights = weights / np.sum(weights)
            # sample n points(intervals)
            random_choices = np.random.choice(x, size=(batch_size - sample_ind), replace=False, p=weights)
            choices[sample_ind:] = random_choices

        # add some random noise to each sample to prevent choosing same points multiple times
        half_spacing = (f_end - f_start) / (2 * (nevals - 1))
        separation = 20 * half_spacing

        # If still too close to each other, shift the points
        def separate_sample(sample, others, threshold, shift):
            if np.any(np.abs(sample - others) < threshold):
                nsample = sample + np.random.choice([1, -1], 1)[0] * shift
                return separate_sample(nsample, others, threshold, shift * 2)
            else:
                return sample

        for ind in range(batch_size):
            choices[ind] = separate_sample(
                choices[ind], np.concatenate((f_sampled, np.delete(choices, ind))), separation, separation / 2
            )

        return choices

    s_error = float("inf")
    iteration_count = 1
    prev_func_re = None
    prev_func_im = None
    min_func_re = None
    min_func_im = None
    s_mag_fit = None

    f_all, s_all = np.array([]), np.array([])

    while s_error > max_delta_s and iteration_count < max_iter:
        if iteration_count == 1:
            # First batch is sampled linearly and is 2 times larger than the next ones
            cur_freqs = np.linspace(start_f, end_f, 2 * frequency_batch)
        else:
            if fit_magnitude:
                prev_func_mag = prev_func_re
            else:

                def prev_func_mag(f):
                    return mag_from_components(prev_func_re(f), prev_func_im(f))

            cur_freqs = _sample_on_slope(prev_func_mag, f_all, s_mag_fit, frequency_batch)

        # create sifs, needs correct frequencies and sif names in json data
        json_data_current_batch = copy.deepcopy(json_data)
        sif_names = [simname + "_f" + str(f).replace(".", "_") for f in cur_freqs]
        json_data_current_batch["sif_names"] = sif_names
        json_data_current_batch["frequency"] = cur_freqs.tolist()
        produce_sif_files(json_data_current_batch, exec_path_override.joinpath(simname))

        # run elmer
        _run_elmer_solver(
            sim_name=simname,
            sif_names=sif_names,
            n_parallel_simulations=n_parallel_simulations,
            n_processes=n_processes,
            n_threads=n_threads,
            exec_path_override=exec_path_override,
        )

        s_new = []
        for f in cur_freqs:
            smatrix_filaname = f'SMatrix_{simname}_f{str(f).replace(".", "_")}.dat'
            s_new.append(
                np.array(
                    read_result_smatrix(smatrix_filaname, path=exec_path_override.joinpath(simname), polar_form=False)
                )
            )

        s_new = np.stack(s_new, axis=0)
        if iteration_count == 1:
            s_all = s_new
            f_all = cur_freqs
        else:
            s_all = np.concatenate((s_all, s_new))
            f_all = np.concatenate((f_all, cur_freqs))

        sort_index = f_all.argsort()
        f_all, s_all = f_all[sort_index], s_all[sort_index, :, :, :]

        s_mag_fit = mag_from_components(s_all[:, 0, fit_index, 0], s_all[:, 0, fit_index, 1])

        if fit_magnitude:
            min_func_re, orders_re = sweep_orders_and_fit(f_all, s_mag_fit)
        else:
            min_func_re, orders_re = sweep_orders_and_fit(f_all, s_all[:, 0, fit_index, 0])
            min_func_im, orders_im = sweep_orders_and_fit(f_all, s_all[:, 0, fit_index, 1])

        # error norm between the fitted function and previous fitted function on all frequencies
        if iteration_count > 1:
            new_s = min_func_re(json_freqs)
            old_s = prev_func_re(json_freqs)  # pylint: disable=E1102
            s_error = np.mean(np.abs(new_s - old_s) / np.abs(new_s))

            if not fit_magnitude:
                new_s = min_func_im(json_freqs)
                old_s = prev_func_im(json_freqs)  # pylint: disable=E1102
                s_error_im = np.mean(np.abs(new_s - old_s) / np.abs(new_s))
                s_error = (s_error + s_error_im) / 2
                print(f"iteration: {iteration_count}, delta_s_re/im: {s_error}, orders: re {orders_re} im {orders_im}")
            else:
                print(f"iteration: {iteration_count}, delta_s_mag: {s_error}, orders: mag {orders_re}")

        if fit_magnitude:
            s_mag_plot = min_func_re(json_freqs)
            plot_filename = f"it_{iteration_count}_mag_{orders_re}.png"
        else:
            s_mag_plot = mag_from_components(min_func_re(json_freqs), min_func_im(json_freqs))
            plot_filename = f"it_{iteration_count}_re_{orders_re}_im_{orders_im}.png"

        if plot_results:
            fig, ax = plt.subplots()
            ax.plot(json_freqs, s_mag_plot)
            ax.plot(f_all, s_mag_fit, "x")
            for xc in cur_freqs:
                ax.axvline(x=xc, color="r", ls="--", lw=0.5)
            ax.set_xlabel("Frequency (GHz)")
            ax.set_ylabel(f"S1{fit_index + 1} Mag")
            fig.savefig(f"{image_folder}/{plot_filename}")
            plt.close()

        prev_func_re, prev_func_im = min_func_re, min_func_im
        iteration_count += 1

    if iteration_count == max_iter:
        logging.warning(f"Failed to converge in {max_iter} iterations")
    else:
        print("Convergence found!")
    n_ports = s_all.shape[1]
    s_result = np.zeros([len(json_freqs), n_ports, n_ports, 2])

    # After converging enough for S11 (or entry given by fit_index), fit all the others entries of S-matrix
    # For now the result fitting will be done separately for real and imaginary part
    # Fitting the phase angle would require some proper way of fitting complex values
    cur_freqs = []
    for i in range(n_ports):
        for j in range(n_ports):
            for part in range(2):
                min_func, _ = sweep_orders_and_fit(f_all, s_all[:, i, j, part])
                s_result[:, i, j, part] = min_func(json_freqs)

            s_mag_interp = mag_from_components(s_result[:, i, j, 0], s_result[:, i, j, 1])
            s_mag_data = mag_from_components(s_all[:, i, j, 0], s_all[:, i, j, 1])

            if plot_results:
                fig, ax = plt.subplots()
                ax.plot(json_freqs, s_mag_interp)
                ax.plot(f_all, s_mag_data, "x")
                ax.set_xlabel("Frequency (GHz)")
                ax.set_ylabel(f"S{i+1}{j+1} Mag")
                fig.savefig(f"{image_folder}/Result_S{i+1}{j+1}_MAG.png")
                plt.close()

    for ind, f in enumerate(json_freqs):
        smatrix_path = exec_path_override.joinpath(f'SMatrix_{simname}_f{str(f).replace(".", "_")}.dat')
        cur_s_re = s_result[ind, :, :, 0]
        cur_s_im = s_result[ind, :, :, 1]
        cur_s_abs = mag_from_components(cur_s_re, cur_s_im)

        with open(smatrix_path, "w") as f:
            for i in range(n_ports):
                f.write("".join([f"{e}        " for e in cur_s_re[i, :]] + ["\n"]))

        with open(str(smatrix_path) + "_im", "w") as f:
            for i in range(n_ports):
                f.write("".join([f"{e}        " for e in cur_s_im[i, :]] + ["\n"]))

        with open(str(smatrix_path) + "_abs", "w") as f:
            for i in range(n_ports):
                f.write("".join([f"{e}        " for e in cur_s_abs[i, :]] + ["\n"]))
