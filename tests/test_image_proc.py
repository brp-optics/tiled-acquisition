from tiled_acquisition.main import looks_like_pmt_shut_off, unaccumulate_images
import numpy as np


def test_unaccumulate_images():
    assert np.all(unaccumulate_images([np.eye(3)]) == np.eye(3))
    assert np.all(
        unaccumulate_images([np.eye(3), np.eye(3)]) == [np.eye(3), np.zeros((3, 3))]
    )


def test_looks_like_pmt_shut_off_basic():
    assert not looks_like_pmt_shut_off(np.eye(3))
    assert looks_like_pmt_shut_off(np.zeros(3))


def test_looks_like_pmt_shut_off_detects_when_last_16K_pixels_are_zero():
    img = np.ones((256, 256))
    img.ravel()[-16384:] = 0
    assert looks_like_pmt_shut_off(img)
    img.ravel()[-16384] = 1
    assert not looks_like_pmt_shut_off(img)
