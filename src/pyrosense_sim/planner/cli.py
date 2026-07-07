"""Command-line interface of the site-planner.

Thin orchestration layer: parses arguments, loads inputs at the
boundary and delegates everything to the domain objects. Installed as
the ``site-planner`` console script.

Example:
    site-planner generate --dem data/dem_cerros_orientales.tif \\
        --aoi config/reserva.geojson --config config/params.yaml \\
        --out out/ --preview
"""

import json
from pathlib import Path
from typing import Annotated

import typer
from shapely.geometry import Polygon, shape

from pyrosense_sim.planner.params import load_params
from pyrosense_sim.planner.site_plan import SitePlan
from pyrosense_sim.planner.terrain import TerrainModel
from pyrosense_sim.planner.zones import ZoneSet

app = typer.Typer(
    name="site-planner",
    help="Genera el plan de despliegue de sensores PyroSense desde un DEM y un AOI.",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """Site-planner de PyroSense: del terreno real al plan de despliegue."""


@app.command()
def generate(
    dem: Annotated[Path, typer.Option(exists=True, dir_okay=False, help="DEM GeoTIFF del área.")],
    aoi: Annotated[
        Path,
        typer.Option(exists=True, dir_okay=False, help="GeoJSON con el polígono del AOI."),
    ],
    config: Annotated[
        Path | None,
        typer.Option(exists=True, dir_okay=False, help="YAML de parámetros (opcional)."),
    ] = None,
    out: Annotated[Path, typer.Option(help="Directorio de salida.")] = Path("out"),
    preview: Annotated[
        bool, typer.Option(help="Genera preview.png (requiere el extra 'preview').")
    ] = False,
) -> None:
    """Generate sensores.geojson, gateways.geojson and site-report.md."""
    params = load_params(config)
    terrain = TerrainModel(dem)
    aoi_polygon = _load_aoi(aoi)
    zones = (
        ZoneSet.from_geojson(params.zones_geojson)
        if params.zones_geojson is not None
        else ZoneSet.derive_default(aoi_polygon, t1_buffer_m=params.t1_buffer_m)
    )
    plan = SitePlan.generate(terrain, zones, params)
    plan.write(out)
    if preview:
        from pyrosense_sim.planner.preview import render_preview

        render_preview(terrain, plan, out / "preview.png")
    typer.echo(
        f"Plan generado: {len(plan.nodes)} nodos, {len(plan.gateways)} gateways, "
        f"{plan.relocated_count} reubicados, {plan.dropped_count} descartados -> {out}/"
    )


def _load_aoi(path: Path) -> Polygon:
    """Read the AOI polygon from a GeoJSON FeatureCollection, Feature or geometry.

    Raises:
        ValueError: If the file holds no polygon geometry.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("type") == "FeatureCollection":
        features = raw.get("features") or []
        if not features:
            msg = f"AOI file {path} has an empty FeatureCollection"
            raise ValueError(msg)
        geometry = shape(features[0]["geometry"])
    elif raw.get("type") == "Feature":
        geometry = shape(raw["geometry"])
    else:
        geometry = shape(raw)
    if not isinstance(geometry, Polygon):
        msg = f"AOI must be a Polygon, got {geometry.geom_type}"
        raise ValueError(msg)
    return geometry


def main() -> None:
    """Console-script entry point."""
    app()
