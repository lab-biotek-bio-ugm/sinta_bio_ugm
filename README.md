# sinta_life_sciences

This repository contains the code and data for scraping and analyzing data from SINTA (Science and Technology Index) for the Biology Faculty at UGM (Universitas Gadjah Mada) and also other life science researchers at 4 other Indonesian Universities

## Getting Started

These instructions will guide you on how to run the analysis on your local machine.

### Prerequisites

You need to have Mamba installed on your machine.

### Installing

1. Clone this repository to your local machine:

```bash
git clone https://github.com/yourusername/sinta_bio_ugm.git
```

2. Navigate to the cloned repository:

```bash
cd sinta_bio_ugm
```

3. Install the required Python packages using the provided env.yaml file:

```bash
mamba env create -f env.yaml
```

### Running the Analysis
1. Activate the conda environment:

```bash
conda activate your_env_name
```

2. Navigate to the notebooks_UGM directory (or the other notebooks):

```bash
cd notebooks_UGM
```

3. Run the Jupyter notebooks in order:

```bash
jupyter notebook 00_data_scraping.ipynb
jupyter notebook 01_EDA.ipynb
jupyter notebook 02_co-author-network.ipynb
```

The `00_data_scraping.ipynb` notebook scrapes the data, `01_EDA.ipynb` performs exploratory data analysis, and `02_co-author-network.ipynb` creates a co-author network.

### Results
The results of the analysis are stored in the figures directory. The scraped data is stored in the data directory.
