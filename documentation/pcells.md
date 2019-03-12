## Launcher
Launcher for connecting wirebonds. Deafault wirebond direction to west, waveguide to east. Uses default ratio `a` and `b` for scaling the gap.

**Parameters:**
- Taper length (um) - from waveguide port to the rectangular part of the launcher pad.
- Pad width (um) - also used for the length of the launcher pad.
- Name shown on annotation layer

**Origin:** Waveguide port

![launcher](/documentation/images/launcher.png)

## Coupler square
Two ports with reference points. The arm leading to the finger has the same width as fingers. The feedline has the same length as the width of the ground gap around the coupler.

**Parameters:**
- `finger_number` - Number of fingers
- `finger_width` - Width of a finger (um)
- `finger_gap` - Gap between the fingers (um)
- `finger_length` - Length of the fingers (um)
- `ground_padding` - Length of the taper (um)
- `corner_r` - Corner radius (um)

**Origin:** Center

![fingercaps](/documentation/images/fingercaps.png)


## Coupler tapered
Two ports with reference points. Ground plane gap is automatically adjusted to maintain the a/b ratio.

**Parameters:**
- `finger_number` - Number of fingers
- `finger_width` - Width of a finger (um)
- `finger_gap` - Gap between the fingers (um)
- `finger_length` - Length of the fingers (um)
- `taper_length` - Length of the taper (um)
- `corner_r` - Corner radius (um)

**Origin:** Center

![fingercapt](/documentation/images/fingercapt.png)

## Waveguide
Coplanar waveguide defined by the width of the center conductor and gap. It can follow any segmented lines with predefined bending radios. It actually consists of straight and bent PCells.

**Warning** Arbitrary angle bents actually have very small gaps between bends and steight segments due to precision of arithmetic. To be fixed in a future release.

**Parameters:**
- `path`, self.TypeShape, "TLine", default = `pya.DPath([pya.DPoint(0,0),pya.DPoint(100,0)],0)`
- `term1` - Termination length start (um) - length of extra ground gap for opened transmission lines
- `term2` - Termination length end (um) - length of extra ground gap for opened transmission lines
- `a` - Width of the center conductor
- `b` - Width of the gap around the center conductor

**Origin:** One port or follows the absolute coordinates of the path.

![waveguide](/documentation/images/waveguide.png)
![waveguide2](/documentation/images/waveguide2.png)

## Meander
Defined by two points, total length and number of meanders. Uses the same bending radious as the underling waveguide.

**Parameters:**
- `start` - Start,  default = `pya.DPoint(0,0)`
- `end` - End
- `length` - Length (um)
- `meanders` - Number of meanders (at least 2). Each perembendicular segment is a meander.

**Origin:** abolute position of `start` 

![meander](/documentation/images/meander.png)



## Qubit "Swissmon"
Swissmon type qubit. Each arm (West, North, East, South) has it's own width. "Hole" for the island has the same `gap_width` for each arm. SQUID is loaded from anouther library. Option of having fluxline. Refpoints for 3 couplers, fluxline position and chargeline position.

**Parameters:**
- `len_direct` - Length between the ports (um) - from waveguide port to the rectangular part of the launcher pad.
- `len_finger` - Length of the fingers (um) - also used for the length of the launcher pad.
- `arm_length` - Arm length (um)
- `arm_width` - Arm width (um, WNES) - list, order West, North, East, South, eg. [24, 24, 24, 24]
- `gap_width` - Gap width (um)
- `fluxline` - Fluxline - True/False.
- `cpl_width` - Coupler width (um, ENW)
- `cpl_length` - Coupler lengths (um, ENW)
- `cpl_gap` - Coupler gap (um, ENW)
- `squid_name` - SQUID Type - Name of the cell from the SQUID library, default = "QCD1"

**Origin:** Center of the cross.

![swissmon](/documentation/images/swissmon.png)

## Chip base
Etching away the metal for dicing track, standard labels in the four courners.

**Parameters:**
- `box` - defines the area `pya.DBox(pya.DPoint(0,0),pya.DPoint(10000,10000)))`
- `dice_width` - Dicing width (um) default = 100
- `name_mask` - Name of the mask, like "M99"
- `name_chip` - Name of the chip on the mask, like "CTest", should not include the name of the mask
- `name_copy` - Name of the copy, usually written at the mask generation step
- `text_margin` - Margin for labels, determines the distanace from the edge and the size of the ground grid safety region.
- `dice_grid_margin` - Margin between dicing edge and ground grid, default = 100, hidden parameter

**Origin:** Center of the cross.

![chipbase](/documentation/images/chipbase.png)
