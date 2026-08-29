# CurviWound Profiler

CurviWound Profiler is research software for quantitative analysis of experimental animal wound images. The workflow combines image renaming, reference-grid processing, curved-surface correction, wound-boundary fitting, wound-area measurement, and ROI-based result review.

## Main functions

- Standardized renaming of experimental wound images
- Detection and manual correction of spatial reference markers
- Editing and saving of reference-grid row/column indices
- Geometric correction and normalization of wound photographs acquired from curved skin surfaces
- Interactive wound-boundary annotation and fitting
- Calculation of wound area using the calibrated image scale
- Management of multiple ROIs
- Saving of fitted-boundary parameters and ROI-related outputs
- Visual review and downstream ROI processing

## Intended use

This software was developed for academic research involving experimental animal wound-healing images, including longitudinal and batch image analysis.

It is research software and is not intended for clinical diagnosis, treatment decisions, or direct patient care.

## Version

**V1.0**

## Author

**Zonghan Gan甘宗瀚**

---

# Repository structure

The repository is divided into three main processing components:

```text
Curviwound-Analyzer/
├── 250424-ocr-renaming.ipynb
├── Distort/
│   ├── data/
│   │   ├── src/
│   │   ├── points/
│   │   ├── gridDict/
│   │   └── dst/
│   ├── generationFile/
│   ├── EN-mainWindow.ui
│   ├── mainWindow.py
│   ├── mainWindow.ui
│   ├── requirements.txt
│   └── undistor.py
└── ROI/
    ├── data/
    │   ├── src/
    │   ├── dst/
    │   ├── ellipse_info/
    │   ├── roi_images/
    │   └── roi_points/
    ├── generationFile/
    ├── mainWindow.py
    ├── mainWindow.ui
    ├── requirements.txt
    └── roi_tmp.py
```

![Repository root](docs/images/repository_root.png)

The `Distort` and `ROI` folders are separate processing stages and each has its own program files, dependency list, user-interface files, and `data` directory.

---

# Workflow overview

The recommended workflow is:

```text
Raw wound photographs
        │
        ▼
250424-ocr-renaming.ipynb
Standardize image filenames by OCR
        │
        ▼
Distort/data/src/
        │
        ▼
Distort/mainWindow.py
Detect / correct reference markers
and check grid row-column indices
        │
        ├──► Distort/data/points/
        └──► Distort/data/gridDict/
        │
        ▼
Distort/undistor.py
Curved-surface geometric correction
        │
        ▼
Distort/data/dst/
Corrected and normalized wound images
        │
        │ copy corrected images
        ▼
ROI/data/src/
        │
        ▼
ROI/mainWindow.py
Wound-boundary annotation,
ellipse fitting and area measurement
        │
        ├──► ROI/data/roi_points/
        ├──► ROI/data/roi_images/
        ├──► ROI/data/ellipse_info/
        └──► ROI/data/dst/
        │
        ▼
ROI post-processing / review
using saved ROI and ellipse information
```

The image below illustrates the overall concept: an animal wound photograph containing a reference grid is geometrically standardized before the wound regions are quantitatively fitted and measured.

![Workflow example](docs/images/workflow_example.png)

---

# Installation

The `Distort` and `ROI` stages each contain a `requirements.txt` file. Install the dependencies for the stage you are going to run.

For the distortion-correction stage:

```bash
cd Distort
pip install -r requirements.txt
```

For the ROI-analysis stage:

```bash
cd ROI
pip install -r requirements.txt
```

Using a dedicated Python environment is recommended.

---

# Step 1 — Rename the raw images

The first processing step is performed with:

```text
250424-ocr-renaming.ipynb
```

This notebook is located in the **root directory** of the repository.

Its purpose is to standardize the filenames of the wound photographs before they enter the downstream analysis workflow. It uses OCR to identify the experimental label visible in the image and renames the corresponding image according to the detected animal / time-point information.

Run the notebook before moving images into the `Distort` workflow.

After renaming, verify the filenames manually. Consistent filenames are important because later stages use the image name to associate photographs with saved reference-point, grid-mapping, ROI, and JSON data.

Do not rename an image after it has already been processed by the later stages unless the corresponding derived files are renamed consistently as well.

---

# Step 2 — Place renamed images in `Distort/data/src`

After the OCR-renaming step, copy the renamed wound photographs into:

```text
Distort/data/src/
```

The `Distort/data` directory has the following structure:

```text
Distort/data/
├── src/        # renamed original wound photographs
├── points/     # saved reference-marker coordinates
├── gridDict/   # saved reference-grid index/mapping data
└── dst/        # geometrically corrected output images
```



For a batch analysis, place all images belonging to that batch in `Distort/data/src/` before starting the marker-processing program.

---

# Step 3 — Detect and correct the reference grid

From the `Distort` directory, run:

```bash
python mainWindow.py
```

This opens the graphical interface used to process the spatial reference markers.

## 3.1 Select an image

Choose an image from the image list and confirm that it displays correctly.

For batch processing, the program can be used to move through the images sequentially.

Useful shortcuts include:

| Shortcut | Function |
|---|---|
| `A` | Enter reference-point addition mode |
| `D` | Enter reference-point deletion mode |
| `W` | Finish the current editing mode |
| `S` | Save the current image data |
| `Page Up` | Previous image |
| `Page Down` | Next image |

## 3.2 Automatic marker detection

Use the image-processing function to identify the reference markers.

After automatic detection, inspect the complete grid rather than saving immediately. Check for:

- missed reference points;
- duplicated points;
- points detected outside the intended grid;
- inaccurate points close to the wound, reflections, or image boundaries.

If only a few points are incorrect, correct them manually.

## 3.3 Add missing reference points

Enter the point-addition mode and click the centre of each missing reference marker.

Zooming into the image before adding a point can improve placement accuracy.

## 3.4 Delete incorrect reference points

Enter the point-deletion mode and use the lasso operation around one or more incorrect markers.

If a correct point is accidentally removed, add it again before saving.

---

# Step 4 — Check the grid row/column indices

After the marker positions are correct, enter the manual grid-index mode.

Each reference point is assigned a grid index in the form:

```text
row,column
```

Check that:

- the row numbers are continuous;
- the column numbers are continuous;
- the indexing direction is consistent;
- every index corresponds to the correct physical reference marker.

If an index is wrong, edit the row/column value.

Changing the index does **not** change the X/Y pixel location of the reference marker.

When the grid is correct, finish the editing operation.

---

# Step 5 — Save the reference-marker and grid data

Save the processed image data before proceeding to geometric correction.

The marker-processing stage writes the relevant results to:

```text
Distort/data/points/
Distort/data/gridDict/
```

`points/` stores reference-marker coordinate information.

`gridDict/` stores the relationship between the reference points and their grid row/column indices, which is required for the geometric correction step.

Before continuing, confirm that every image to be corrected has the required corresponding data.

---

# Step 6 — Perform curved-surface correction

From the `Distort` directory, run:

```bash
python undistor.py
```

This stage reads the original wound images together with the saved grid mapping and performs the curved-surface geometric correction / normalization.

The main input relationship is:

```text
Distort/data/src/
        +
Distort/data/gridDict/
        │
        ▼
Distort/undistor.py
        │
        ▼
Distort/data/dst/
```

Corrected images are written to:

```text
Distort/data/dst/
```

Do not move or rename the source images or their grid data while this process is running.

## Check the corrected images

After processing, inspect the images in `Distort/data/dst/`.

Check that:

1. the expected wound and reference-grid area is retained;
2. the grid is more regular after correction;
3. the wound region is not visibly broken or severely stretched;
4. there are no obvious abnormal blank regions.

If a corrected image is clearly abnormal, return to `Distort/mainWindow.py` and recheck the marker locations and grid indices for that image.

---

# Step 7 — Transfer corrected images to the ROI stage

The ROI analysis is a separate stage with its own folder structure.

Copy the corrected images that you want to measure from:

```text
Distort/data/dst/
```

to:

```text
ROI/data/src/
```

Keep the filenames unchanged.

The ROI data structure is:

```text
ROI/data/
├── src/            # corrected images used for ROI measurement
├── dst/            # saved processed / result images
├── ellipse_info/   # fitted ellipse parameters saved in JSON form
├── roi_images/     # saved ROI image outputs
└── roi_points/     # saved wound-boundary point data
```



Keeping filenames unchanged is important because the ROI results are associated with the source image name.

---

# Step 8 — Wound-boundary fitting and area measurement

From the `ROI` directory, install its requirements if necessary and run:

```bash
python mainWindow.py
```

This opens the wound-region measurement interface.

The recommended operation sequence for each image is:

```text
Select image
→ Select ROI
→ Adjust the display if needed
→ Add wound-boundary points
→ Inspect the fitted boundary
→ Delete / replace inaccurate points
→ Finish editing
→ Save
```

## 8.1 Select the ROI

The program supports multiple ROI identifiers.

For a single wound, use the same ROI number consistently.

For several wound regions in one image, assign different ROI numbers and keep the same numbering convention across the experimental time series wherever possible.

## 8.2 Add wound-boundary points

Enter the wound-boundary point acquisition mode and click along the visible wound edge.

At least **5 points** are required for ellipse fitting.

The first points should be distributed around different parts of the wound rather than concentrated on one side.

Once the fitted outline is displayed, compare the entire fitted boundary with the visible wound margin and add additional points where necessary.

## 8.3 Correct the fitted boundary

If a point is inaccurate, use the deletion mode and remove it with the lasso function, then add a replacement point.

The ROI stage supports:

| Shortcut | Function |
|---|---|
| `A` | Add wound-boundary points |
| `D` | Delete wound-boundary points |
| `W` | Finish the current editing mode |
| `S` | Save the current image |
| `Page Up` | Previous image |
| `Page Down` | Next image |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |

Contrast adjustment can be used to make unclear wound edges easier to identify.

## 8.4 Finish and save

**Finish** only exits the current editing mode. It does not replace the save operation.

After confirming the wound boundary, save the image/ROI result.

The ROI workflow stores its outputs under `ROI/data/`, including:

```text
ROI/data/roi_points/
ROI/data/roi_images/
ROI/data/ellipse_info/
ROI/data/dst/
```

The saved ellipse information records the fitted boundary parameters used for subsequent review and ROI processing. The area results generated by the measurement step are reported using the calibrated physical image scale.

---

# Step 9 — Review the saved wound boundaries

The fitted-boundary information stored in:

```text
ROI/data/ellipse_info/
```

can be used together with the corresponding images to reconstruct and visually review the saved wound outlines.

The purpose of this review is to confirm:

- the correct wound / ROI was measured;
- the fitted centre is in the expected location;
- the boundary size is appropriate;
- the long- and short-axis directions are reasonable;
- the fitted boundary agrees with the visible wound edge.

If a result is clearly incorrect, return to the ROI measurement interface, correct the boundary points, and save the result again.

---

# Step 10 — ROI post-processing

The `ROI` directory also contains:

```text
roi_tmp.py
```

This is the repository's downstream ROI-processing utility associated with the saved ROI / ellipse information.

Before running it, confirm that the required images and saved ROI/ellipse data are present in the corresponding `ROI/data/` folders and that filenames have not been changed.

Because this script is used after the main ROI measurement step, review the paths configured in the script before batch execution so that they point to the intended `ROI/data` inputs and outputs.

---

# Complete batch workflow

For routine use, follow this order:

```text
1. Raw experimental wound photographs
2. 250424-ocr-renaming.ipynb
   └─ standardize filenames
3. Copy renamed images to Distort/data/src/
4. Distort/mainWindow.py
   ├─ automatic reference-marker detection
   ├─ manual point correction
   ├─ grid row/column index correction
   └─ save to points/ and gridDict/
5. Distort/undistor.py
   └─ corrected images written to Distort/data/dst/
6. Copy selected corrected images
   Distort/data/dst/ → ROI/data/src/
7. ROI/mainWindow.py
   ├─ select ROI
   ├─ annotate wound boundary
   ├─ fit wound boundary
   ├─ calculate wound area
   └─ save ROI-related results
8. Review saved ellipse / ROI results
9. Run ROI post-processing as required
```

For longitudinal experiments, consistent image names and ROI numbers should be maintained across time points.

---

# Troubleshooting

## OCR renaming gives an incorrect filename

Manually check the detected experimental label before starting the `Distort` stage. Correct the filename before the image is propagated through the later workflow.

## An image is not shown in the Distort interface

Confirm that the image is located in:

```text
Distort/data/src/
```

and that it can be opened normally by a standard image viewer.

## Many reference markers are missed

Check the visibility of the reference grid and adjust the image-processing parameters if needed. Manually add remaining missed points.

## The corrected image is missing

Check that the source image has corresponding grid information in:

```text
Distort/data/gridDict/
```

## The corrected image is severely distorted

Return to the marker-processing stage and verify both the reference-point positions and the grid row/column indices.

## An image does not appear in the ROI interface

Confirm that the corrected image has been copied to:

```text
ROI/data/src/
```

## A fitted wound boundary is poor

Redistribute the boundary points around the complete wound edge, remove inaccurate points, and add replacement points before saving.

---

# Citation

If this software contributes to published research, please cite the associated research article and/or software record when complete citation information becomes available.

Structured citation metadata may be provided separately in `CITATION.cff`.

---

# Research data and responsible use

Users are responsible for ensuring that images and associated metadata processed with this software are handled in accordance with applicable institutional, ethical, privacy, and data-governance requirements.

Results generated by the software should be reviewed and interpreted in the context of the relevant experimental design.

## Disclaimer

CurviWound Profiler is research software. Its outputs are intended to assist quantitative analysis of experimental animal wound images and should be independently reviewed where appropriate.
