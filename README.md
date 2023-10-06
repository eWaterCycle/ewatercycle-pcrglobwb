# eWaterCycle plugin for PCRGlobWB hydrological model

[![Research Software Directory Badge](https://img.shields.io/badge/rsd-00a3e3.svg)](https://www.research-software.nl/software/ewatercycle-pcrglobwb)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8413752.svg)](https://doi.org/10.5281/zenodo.8413752)
[![PyPI](https://img.shields.io/pypi/v/ewatercycle-pcrglobwb)](https://pypi.org/project/ewatercycle-pcrglobwb/)

[eWatercycle](https://ewatercycle.readthedocs.io/) plugin for PCRGlobWB model.

PCRGLOBWB (PCRaster Global Water Balance) is a large-scale hydrological model with documentation at https://globalhydrology.nl/research/models/pcr-globwb-1-0/ .

## Installation

eWaterCycle must be installed in a [mamba](https://conda-forge.org/miniforge/) environment. The environment can be created with

```console
wget https://raw.githubusercontent.com/eWaterCycle/ewatercycle/main/environment.yml
mamba env create --name ewatercycle-pcrglobwb --file environment.yml
conda activate ewatercycle-pcrglobwb
```

Install this package alongside your eWaterCycle installation

```console
pip install ewatercycle-pcrglobwb
```

Then PCRGlobWB becomes available as one of the eWaterCycle models

```python
from ewatercycle.models import PCRGlobWB
```

## Usage

Usage of PCRGlobWB forcing generation and model execution is shown in 
[docs/generate_forcing.ipynb](https://github.com/eWaterCycle/ewatercycle-pcrglobwb/tree/main/docs/generate_forcing.ipynb) and [docs/model.ipynb](https://github.com/eWaterCycle/ewatercycle-pcrglobwb/tree/main/docs/model.ipynb) respectively.

Irrigation example at [docs/Irrigation.ipynb](https://github.com/eWaterCycle/ewatercycle-pcrglobwb/tree/main/docs/Irrigation.ipynb).

## License

`ewatercycle-pcrglobwb` is distributed under the terms of the [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) license.
