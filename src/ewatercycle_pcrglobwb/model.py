"""eWaterCycle wrapper around PCRGlobWB BMI."""

import logging
from os import PathLike
from typing import Any, ItemsView, Iterable, Optional

import bmipy
import numpy as np
import xarray as xr
from pathlib import Path
from grpc4bmi.bmi_memoized import MemoizedBmi
from grpc4bmi.bmi_optionaldest import OptionalDestBmi
from pydantic import PrivateAttr, model_validator

from ewatercycle.base.model import ContainerizedModel
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.container import BmiProxy, ContainerImage, start_container
from ewatercycle_pcrglobwb.forcing import PCRGlobWBForcing
from ewatercycle.util import CaseConfigParser, get_time, to_absolute_path

logger = logging.getLogger(__name__)


class _SwapXY(BmiProxy):
    """Corrective glasses for pcrg model in container images.

    The model in the images defined in :pt:const:`_version_images` have swapped x and y coordinates.

    At https://bmi.readthedocs.io/en/stable/model_grids.html#model-grids it says that
    that x are columns or longitude and y are rows or latitude.
    While in the image the get_grid_x method returned latitude and get_grid_y method returned longitude.
    """

    def get_grid_x(self, grid: int, x: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_y(grid, x)

    def get_grid_y(self, grid: int, y: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_x(grid, y)


class PCRGlobWB(ContainerizedModel):
    """eWaterCycle implementation of PCRGlobWB hydrological model.

    Args:
        parameter_set: instance of
            :py:class:`~ewatercycle.parameter_sets.default.ParameterSet`.
        forcing: ewatercycle forcing container;
            see :py:mod:`ewatercycle.forcing`.

    """

    forcing: Optional[PCRGlobWBForcing] = None
    parameter_set: ParameterSet  # not optional for this model
    cloneMap: str | Path | None = None
    landmask: str | Path | None = None
    bmi_image: ContainerImage = ContainerImage("ghcr.io/ewatercycle/pcrglobwb-grpc4bmi:v0.2.3")

    _config: CaseConfigParser = PrivateAttr()

    @model_validator(mode="after")
    def _initialize_config(self: "PCRGlobWB") -> "PCRGlobWB":
        cfg = CaseConfigParser()
        cfg.read(self.parameter_set.config)
        cfg.set("globalOptions", "inputDir", str(self.parameter_set.directory))

        if self.forcing:
            assert self.forcing.temperatureNC is not None  # TODO fix forcing class.
            assert self.forcing.precipitationNC is not None
            cfg.set(
                "globalOptions",
                "startTime",
                get_time(self.forcing.start_time).strftime("%Y-%m-%d"),
            )
            cfg.set(
                "globalOptions",
                "endTime",
                get_time(self.forcing.start_time).strftime("%Y-%m-%d"),
            )
            cfg.set(
                "meteoOptions",
                "temperatureNC",
                str(
                    to_absolute_path(
                        self.forcing.temperatureNC,
                        parent=self.forcing.directory,
                        must_be_in_parent=False,
                        must_exist=True,
                    )
                ),
            )
            cfg.set(
                "meteoOptions",
                "precipitationNC",
                str(
                    to_absolute_path(
                        self.forcing.precipitationNC,
                        parent=self.forcing.directory,
                        must_be_in_parent=False,
                        must_exist=True,
                    )
                ),
            )
        if self.cloneMap:
            cfg.set(
                "globalOptions",
                "cloneMap",
                str(
                    to_absolute_path(
                        self.cloneMap,
                        parent=self.parameter_set.directory,
                        must_be_in_parent=False,
                        must_exist=True,
                    )
                ),
            )

        if self.landmask:
            cfg.set(
                "globalOptions",
                "landmask",
                str(
                    to_absolute_path(
                        self.landmask,
                        parent=self.parameter_set.directory,
                        must_be_in_parent=False,
                        must_exist=True,
                    )
                ),
            )

        self._config = cfg
        return self

    @property
    def parameters(self) -> ItemsView[str, Any]:
        """List the parameters for this model."""
        return {
            "start_time": f"{self._config.get('globalOptions', 'startTime')}T00:00:00Z",
            "end_time": f"{self._config.get('globalOptions', 'endTime')}T00:00:00Z",
            "routing_method": self._config.get("routingOptions", "routingMethod"),
            "max_spinups_in_years": self._config.get(
                "globalOptions", "maxSpinUpsInYears"
            ),
        }.items()

    def _make_cfg_file(self, **kwargs):
        self._update_config(**kwargs)
        return self._export_config()

    def _make_bmi_instance(self) -> bmipy.Bmi:
        # Override because need to add _SwapXY wrapper
        if self.parameter_set:
            self._additional_input_dirs.append(str(self.parameter_set.directory))
        if self.forcing:
            self._additional_input_dirs.append(str(self.forcing.directory))

        if self.cloneMap:
            clone_dir = str(Path(self.cloneMap).parent)
            if clone_dir not in self._additional_input_dirs:
                self._additional_input_dirs.append(clone_dir)

        if self.landmask:
            landmask_dir = str(Path(self.landmask).parent)
            if landmask_dir not in self._additional_input_dirs:
                self._additional_input_dirs.append(landmask_dir)

        
        # Remove nested directories when their parent is already mounted.
        dirs = [Path(d).resolve() for d in self._additional_input_dirs]
        filtered_dirs = []

        for d in dirs:
            if not any(
                d != parent and d.is_relative_to(parent)
                for parent in dirs
            ):
                filtered_dirs.append(d)

        self._additional_input_dirs = [str(d) for d in filtered_dirs]

        # Fixed from v0.2.2 onwards
        wrappers = (MemoizedBmi, OptionalDestBmi)
        if self.bmi_image.version in ["setters", "v0.2.0", "v0.2.1"]:
            wrappers += (_SwapXY,)  # tags before <new tag name> needed corrective glasses



        return start_container(
            image=self.bmi_image,
            work_dir=self._cfg_dir,
            input_dirs=self._additional_input_dirs,
            timeout=300,
            wrappers=wrappers,
        )

    def _update_config(self, **kwargs):
        if "start_time" in kwargs:
            self._config.set(
                "globalOptions",
                "startTime",
                get_time(kwargs["start_time"]).strftime("%Y-%m-%d"),
            )

        if "end_time" in kwargs:
            self._config.set(
                "globalOptions",
                "endTime",
                get_time(kwargs["end_time"]).strftime("%Y-%m-%d"),
            )

        if "routing_method" in kwargs:
            self._config.set(
                "routingOptions", "routingMethod", kwargs["routing_method"]
            )

        if "dynamic_flood_plain" in kwargs:
            self._config.set(
                "routingOptions",
                "dynamicFloodPlain",
                kwargs["dynamic_flood_plain"],
            )

        if "max_spinups_in_years" in kwargs:
            self._config.set(
                "globalOptions",
                "maxSpinUpsInYears",
                str(kwargs["max_spinups_in_years"]),
            )

    def _export_config(self) -> PathLike:
        self._config.set("globalOptions", "outputDir", str(self._cfg_dir))
        new_cfg_file = to_absolute_path(
            "pcrglobwb_ewatercycle.ini", parent=self._cfg_dir
        )
        with new_cfg_file.open("w") as filename:
            self._config.write(filename)

        return new_cfg_file

    # Overwrite default methods which do not work due to the BMI being old:
    def get_value_as_xarray(self, name: str) -> xr.DataArray:
        y, x = self._bmi.get_grid_shape(0)
        gridsize = x*y
        dest = np.zeros(gridsize)
        val = self._bmi.get_value(name, dest)

        x_coords = self._bmi.get_grid_x(0, np.zeros(x))
        y_coords = self._bmi.get_grid_y(0, np.zeros(y))
        return xr.DataArray(
            data=val.reshape(y, x),
            coords={"latitude": x_coords, "longitude": y_coords},
            dims=("longitude", "latitude")
        )

    def get_value(self, name):
        y, x = self._bmi.get_grid_shape(0)
        gridsize = x*y
        dest = np.zeros(gridsize)
        return self._bmi.get_value(name, dest)

    def get_value_at_indices(self, name, inds):
        return self.get_value(name)[inds]

    def get_latlon_grid(self, name) -> tuple[Any, Any, Any]:
        grid_id = self._bmi.get_var_grid(name)
        shape = self._bmi.get_grid_shape(grid_id)
        grid_lon = self._bmi.get_grid_x(grid_id, np.zeros(shape[1]))
        grid_lat = self._bmi.get_grid_y(grid_id, np.zeros(shape[0]))
        return grid_lat, grid_lon, shape

    def get_value_at_coords(
        self, name, lat: Iterable[float], lon: Iterable[float]
    ) -> np.ndarray:
        """Get a copy of values of the given variable at lat/lon coordinates.

        Args:
            name: Name of variable
            lat: Latitudinal value
            lon: Longitudinal value
        """
        indices = self._coords_to_indices(name, lat, lon)
        indices = np.array(indices)
        return self.get_value_at_indices(name, indices)
