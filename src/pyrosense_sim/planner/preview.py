"""Optional PNG preview of a site plan (visual verification only).

Kept out of the main dependency set: matplotlib is only needed if the
user passes ``--preview``. Install it with ``pip install "pyrosense-sim[preview]"``.
"""

from pathlib import Path

from pyrosense_sim.planner.site_plan import SitePlan
from pyrosense_sim.planner.terrain import TerrainModel

_TIER_COLORS = {1: "#d62728", 2: "#ff7f0e", 3: "#ffdd57"}


def render_preview(terrain: TerrainModel, plan: SitePlan, path: Path) -> None:
    """Render the DEM in grayscale with nodes and gateways overlaid.

    Args:
        terrain: The terrain the plan was generated over.
        plan: The plan to draw.
        path: Destination PNG file.

    Raises:
        RuntimeError: If matplotlib is not installed (actionable message).
    """
    try:
        import matplotlib
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        msg = "preview requires matplotlib; install with: pip install 'pyrosense-sim[preview]'"
        raise RuntimeError(msg) from exc
    matplotlib.use("Agg")  # headless: we only ever write files
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 8))
    min_lon, min_lat, max_lon, max_lat = terrain.bounds
    ax.imshow(
        terrain.elevation_grid,
        extent=(min_lon, max_lon, min_lat, max_lat),
        origin="upper",
        cmap="gray",
    )
    for tier, color in _TIER_COLORS.items():
        tier_nodes = [node for node in plan.nodes if node.tier == tier]
        if tier_nodes:
            ax.scatter(
                [node.lon for node in tier_nodes],
                [node.lat for node in tier_nodes],
                s=6,
                c=color,
                label=f"T{tier} ({len(tier_nodes)})",
            )
    ax.scatter(
        [gateway.lon for gateway in plan.gateways],
        [gateway.lat for gateway in plan.gateways],
        marker="^",
        s=60,
        c="#1f77b4",
        label=f"Gateways ({len(plan.gateways)})",
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(loc="upper right", fontsize=8)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
