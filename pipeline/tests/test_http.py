from p3d_pipeline.http import throttle_pause


def test_throttle_pause_follows_the_worst_status() -> None:
    header = "Request Count status: Green (2%), Request Time status: Yellow (61%), Service status: Green (20%)"
    assert throttle_pause(header) == 1.0
    assert throttle_pause("Request Count status: Red (90%)") == 5.0
    assert throttle_pause("Request Count status: Green (1%), Request Time status: Green (3%)") == 0.0
    assert throttle_pause(None) == 0.0
