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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


import logging
import importlib.util
import copy
from typing import Any, Callable
from pathlib import Path
from elmer_helpers import read_result_smatrix, produce_sif_files, write_snp_file, read_snp_file
from run_helpers import _run_elmer_solver

from scipy.signal import find_peaks, peak_prominences, peak_widths
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt

has_polyrat = importlib.util.find_spec("polyrat") is not None
if has_polyrat:
    from polyrat import StabilizedSKRationalApproximation as SK_fit


def rational_fit(
    f: np.ndarray, s_data: np.ndarray, num_order: int, denom_order: int
) -> tuple[float, Callable[[np.ndarray], np.ndarray]]:
    """
    Args:
        f             : Independent variable of the fit (frequency)
        s_data        : Dependent variable of the fit (s matrix component)
        min_num_order : Order of the numerator of the fitted rational function
        max_num_order : Order of the denominator of the fitted rational function

    Returns:
        tuple:
         - residual of the fit
         - function of the fit

    """
    if has_polyrat:
        fit_obj = SK_fit(num_order, denom_order, verbose=False, maxiter=50, xtol=1e-9)
        fit_obj.fit(f.reshape(-1, 1), s_data)

        def func(x: np.ndarray) -> np.ndarray:
            return fit_obj(x.reshape(-1, 1))

        residual = float(np.linalg.norm(func(f.reshape(-1, 1)) - s_data))
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
            residual = float(np.linalg.norm(infodict["fvec"]))

            def func(x: np.ndarray) -> np.ndarray:
                return fit_func(x, *popt)

        except RuntimeError:
            logging.warning(
                "Least squares fit failed in interpolated frequency sweep, "
                f"rational order ({num_order}, {denom_order})"
            )
            logging.warning(mesg)
            residual = float("inf")

            def func(x: np.ndarray) -> np.ndarray:
                return x

    return (residual, func)


def sweep_orders_and_fit(
    f_all: np.ndarray,
    s_all: np.ndarray,
    min_num_order: int = 0,
    max_num_order: int = 10,
    min_denom_order: int = 2,
    max_denom_order: int = 20,
) -> tuple[Callable[[np.ndarray], np.ndarray], tuple[int, int]]:
    """
    Args:
        f_all           : All frequencies calculated so far
        s_all           : Single S-matrix component at all of the frequencies
        min_num_order   : minimum order of the numerator of the fitted rational function
        max_num_order   : maximum order of the numerator of the fitted rational function
        min_denom_order : minimum order of the denominator of the fitted rational function
        max_denom_order : maximum order of the denominator of the fitted rational function

    Returns:
        min_func: function of the best fit
        orders: orders of the numerator and denominator for the best fit
    """
    min_residual = float("inf")
    for num_order in range(min_num_order, max_num_order + 1):
        effective_len = len(f_all) if len(f_all) < 10 else len(f_all) // 2
        cur_max_denom_order = min(effective_len - num_order - 1, max_denom_order + 1)
        for denom_order in range(min_denom_order, cur_max_denom_order):
            residual, func = rational_fit(f_all, s_all, num_order, denom_order)
            if residual < min_residual:
                min_residual = residual
                min_func = func
                orders = (num_order, denom_order)

    if min_residual == float("inf"):
        raise RuntimeError("Least squares fit failed with all orders in interpolated frequency sweep.")

    return min_func, orders


def _sample_on_slope(
    func: Callable[[np.ndarray], np.ndarray],
    f_sampled: np.ndarray,
    s_sampled: np.ndarray,
    batch_size: int,
    max_p_factor: float = 5,
    nevals: int = 10000,
) -> np.ndarray:
    """
    Args:
        func         : fitted magnitude of S-matrix component
        f_sampled    : list of frequencies sampled on previous iterations
        s_sampled    : list of S-matrix magnitudes used for the sampling
        batch_size   : how many frequencies are sampled
        max_p_factor : How many times more likely to sample the point with highest gradient
                                vs the point with lowest gradient.
        nevals       : Number of evaluations of func for evaluation of gradients and peak finding

    Returns:
        frequencies for the next batch of simulations

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


def polar_to_cartesian(s_arr: np.ndarray) -> np.ndarray:
    s_mag = s_arr[:, :, :, 0]
    s_angle = np.radians(s_arr[:, :, :, 1])
    s_arr_transf = s_arr.copy()
    s_arr_transf[:, :, :, 0] = s_mag * np.cos(s_angle)
    s_arr_transf[:, :, :, 1] = s_mag * np.sin(s_angle)
    return s_arr_transf


def cartesian_to_polar(s_arr: np.ndarray) -> np.ndarray:
    s_re = s_arr[:, :, :, 0]
    s_im = s_arr[:, :, :, 1]
    s_arr_transf = s_arr.copy()
    s_arr_transf[:, :, :, 0] = np.hypot(s_re, s_im)
    s_arr_transf[:, :, :, 1] = np.degrees(np.arctan2(s_im, s_re))
    return s_arr_transf


def interpolate_s_parameters(
    simulated_frequencies: np.ndarray,
    simulated_smatrix: np.ndarray,
    interpolation_frequencies: np.ndarray,
    polar_form=False,
    plot_results: bool = False,
    image_folder: str = "",
) -> np.ndarray:
    """
    Interpolate S-matrix results. Interpolates each entry and component separately

    Args:
        simulated_frequencies: Frequencies corresponding to the simualted S-matrix results
        simulated_smatrix: 4 dimensional array of simulated S-matrix results S[freq, row, col, component]
        interpolation_frequencies: Frequencies to interpolate the result at
        plot_results: Plot each interpolated S-matrix result
        image_folder: Folder where to save the plots as png images

    Returns:
        Interpolated S-matrix
    """
    if polar_form:
        simulated_smatrix = polar_to_cartesian(simulated_smatrix)

    n_ports = simulated_smatrix.shape[1]
    s_result = np.zeros([len(interpolation_frequencies), n_ports, n_ports, 2])
    for i in range(n_ports):
        for j in range(n_ports):
            for part in range(2):
                min_func, _ = sweep_orders_and_fit(simulated_frequencies, simulated_smatrix[:, i, j, part])
                s_result[:, i, j, part] = min_func(interpolation_frequencies)

            if plot_results:
                s_mag_interp = np.hypot(s_result[:, i, j, 0], s_result[:, i, j, 1])
                s_mag_data = np.hypot(simulated_smatrix[:, i, j, 0], simulated_smatrix[:, i, j, 1])
                fig, ax = plt.subplots()
                ax.plot(interpolation_frequencies, s_mag_interp)
                ax.plot(simulated_frequencies, s_mag_data, "x")
                ax.set_xlabel("Frequency (GHz)")
                ax.set_ylabel(f"S{i+1}{j+1} Mag")
                fig.savefig(f"{image_folder}/Result_S{i+1}{j+1}_MAG.png")
                plt.close()

    if polar_form:
        s_result = cartesian_to_polar(s_result)
    return s_result


def interpolate_s_parameters_from_snp(
    simulated_snp: Path | str,
    interpolated_snp: Path | str,
    interpolation_frequencies: np.ndarray | list,
    plot_results: bool = False,
    image_folder: str = "",
) -> None:
    """Interpolate S-matrix results from an snp file and save the interpolated result to another snp file

    Args:
        simulated_snp: Path for the existing snp file
        interpolated_snp: Where to save the interpolated results
        interpolation_frequencies: Frequencies to interpolate at
        plot_results: Plot each interpolated S-matrix result
        image_folder: Folder where to save the plots as png images
    """
    interpolation_frequencies = np.array(interpolation_frequencies)
    f_sim, s_sim, polar_form, renorm, port_data = read_snp_file(simulated_snp)
    s_int = interpolate_s_parameters(
        f_sim, s_sim, interpolation_frequencies, polar_form, plot_results=plot_results, image_folder=image_folder
    )
    write_snp_file(interpolated_snp, interpolation_frequencies, s_int, polar_form, renorm, port_data)


def interpolating_frequency_sweep(
    json_data: dict[str, Any],
    exec_path_override: Path,
    fit_index: int = 1,
    fit_magnitude: bool = False,
    max_iter: int = 20,
    plot_results: bool = True,
) -> None:
    """
    Run interpolated frequency sweep

    Args:
        json_data           : Simulation data loaded from the .json in simulation tmp folder
        exec_path_override  : Working directory from where the simulations are run
                                (usually KQCircuits/tmp/sim_name)
        fit_index           : Smatrix component S(0, fit_index) used for fitting and interpolating
                                Note that indexing starts from 0, e.g fitindex 0 is S11 and 1 is S12
        fit_magnitude       : If true fits the magnitude component of S(0, fit_index),
                                If False fits real and imaginary parts separately.
                                For now Only applies to intermediate steps. The final result fitting is
                                done separately for real and im parts
        max_iter            : Maximum number of interpolation steps with new simulations
        plot_results        : If True saves plots for intermediate and final S matrix fitting
                                results as png files

    """
    if not has_polyrat:
        logging.warning(
            "Rational fit using scipy.curve_fit is extremely unreliable. Consider installing polyrat library"
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

    start_f = min(json_data["frequency"])
    end_f = max(json_data["frequency"])
    if start_f == end_f:
        raise ValueError(
            f"Cannot do interpolating sweep as only a single frequency was given (f={json_data['frequency']})"
        )

    # error is evaluated based on these points
    eval_freqs = np.linspace(start_f, end_f, 10000)

    frequency_batch = json_data["frequency_batch"]
    max_delta_s = json_data["max_delta_s"]
    simname = json_data["name"]

    s_error = float("inf")
    iteration_count = 1
    prev_func_re = lambda x: x  # initialize with identity function
    prev_func_im = lambda x: x
    s_mag_fit = np.array([])

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
                    return np.hypot(prev_func_re(f), prev_func_im(f))

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

        s_new_list = []
        for f in cur_freqs:
            smatrix_filaname = f'SMatrix_{simname}_f{str(f).replace(".", "_")}.dat'
            s_new_list.append(
                read_result_smatrix(smatrix_filaname, path=exec_path_override.joinpath(simname), polar_form=False)
            )

        s_new = np.stack(s_new_list, axis=0)
        if iteration_count == 1:
            s_all = s_new
            f_all = cur_freqs
        else:
            s_all = np.concatenate((s_all, s_new))
            f_all = np.concatenate((f_all, cur_freqs))

        sort_index = f_all.argsort()
        f_all, s_all = f_all[sort_index], s_all[sort_index, :, :, :]

        s_mag_fit = np.hypot(s_all[:, 0, fit_index, 0], s_all[:, 0, fit_index, 1])

        if fit_magnitude:
            min_func_re, orders_re = sweep_orders_and_fit(f_all, s_mag_fit)
        else:
            min_func_re, orders_re = sweep_orders_and_fit(f_all, s_all[:, 0, fit_index, 0])
            min_func_im, orders_im = sweep_orders_and_fit(f_all, s_all[:, 0, fit_index, 1])

        # error norm between the fitted function and previous fitted function on all frequencies
        if iteration_count > 1:
            new_s = min_func_re(eval_freqs)
            old_s = prev_func_re(eval_freqs)
            s_error = np.mean(np.abs(new_s - old_s) / np.abs(new_s))

            if not fit_magnitude:
                new_s = min_func_im(eval_freqs)
                old_s = prev_func_im(eval_freqs)
                s_error_im = np.mean(np.abs(new_s - old_s) / np.abs(new_s))
                s_error = (s_error + s_error_im) / 2
                print(f"iteration: {iteration_count}, delta_s_re/im: {s_error}, orders: re {orders_re} im {orders_im}")
            else:
                print(f"iteration: {iteration_count}, delta_s_mag: {s_error}, orders: mag {orders_re}")

        if fit_magnitude:
            s_mag_plot = min_func_re(eval_freqs)
            plot_filename = f"it_{iteration_count}_mag_{orders_re}.png"
        else:
            s_mag_plot = np.hypot(min_func_re(eval_freqs), min_func_im(eval_freqs))
            plot_filename = f"it_{iteration_count}_re_{orders_re}_im_{orders_im}.png"

        if plot_results:
            fig, ax = plt.subplots()
            ax.plot(eval_freqs, s_mag_plot)
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
