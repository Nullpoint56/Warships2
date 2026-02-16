from engine.rendering.scene_primitives import grid_positions


def test_grid_positions_shape_and_endpoints() -> None:
    positions = grid_positions(x=0.0, y=0.0, width=10.0, height=20.0, lines=3, z=1.0)
    assert positions.shape == (12, 3)
    assert tuple(positions[0]) == (0.0, 0.0, 1.0)
    assert tuple(positions[1]) == (0.0, 20.0, 1.0)
