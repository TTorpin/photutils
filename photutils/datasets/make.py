# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Make example datasets.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import numpy as np
from astropy.table import Table
from astropy.modeling.models import Gaussian2D
from astropy.convolution import discretize_model
import astropy.units as u

from ..utils import check_random_state


__all__ = ['make_noise_image', 'make_poisson_noise', 'make_gaussian_sources',
           'make_random_gaussians', 'make_4gaussians_image',
           'make_100gaussians_image']


def make_noise_image(image_shape, type='gaussian', mean=None, stddev=None,
                     unit=None, random_state=None):
    """
    Make a noise image containing Gaussian or Poisson noise.

    Parameters
    ----------
    image_shape : 2-tuple of int
        Shape of the output 2D image.

    type : {'gaussian', 'poisson'}
        The distribution used to generate the random noise.

            * ``'gaussian'``: Gaussian distributed noise.
            * ``'poisson'``: Poisson distributed nose.

    mean : float
        The mean of the random distribution.  Required for both Gaussian
        and Poisson noise.

    stddev : float, optional
        The standard deviation of the Gaussian noise to add to the
        output image.  Required for Gaussian noise and ignored for
        Poisson noise (the variance of the Poisson distribution is equal
        to its mean).

    unit : `~astropy.units.UnitBase` instance, str
        An object that represents the unit desired for the output image.
        Must be an `~astropy.units.UnitBase` object or a string parseable
        by the `~astropy.units` package.

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.
        Separate function calls with the same noise parameters and
        ``random_state`` will generate the identical noise image.

    Returns
    -------
    image : `~numpy.ndarray`
        Image containing random noise.

    See Also
    --------
    make_poisson_noise, make_gaussian_sources, make_random_gaussians

    Examples
    --------

    .. plot::
        :include-source:

        # make a Gaussian and Poisson noise image
        from photutils.datasets import make_noise_image
        shape = (100, 200)
        image1 = make_noise_image(shape, type='gaussian', mean=0., stddev=5.)
        image2 = make_noise_image(shape, type='poisson', mean=5.)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
        ax1.imshow(image1, origin='lower', interpolation='nearest')
        ax2.imshow(image2, origin='lower', interpolation='nearest')
    """

    if mean is None:
        raise ValueError('"mean" must be input')
    prng = check_random_state(random_state)
    if type == 'gaussian':
        if stddev is None:
            raise ValueError('"stddev" must be input for Gaussian noise')
        image = prng.normal(loc=mean, scale=stddev, size=image_shape)
    elif type == 'poisson':
        image = prng.poisson(lam=mean, size=image_shape)
    else:
        raise ValueError('Invalid type: {0}. Use one of '
                         '{"gaussian", "poisson"}.'.format(type))

    if unit is not None:
        image = u.Quantity(image, unit=unit)

    return image


def make_poisson_noise(image, random_state=None):
    """
    Make a Poisson noise image from an image whose pixel values
    represent the expected number of counts (e.g., electrons or
    photons).  Each pixel in the output noise image is generated by
    drawing a random sample from a Poisson distribution with expectation
    value given by the input ``image``.

    Parameters
    ----------
    image : `~numpy.ndarray` or `~astropy.units.Quantity`
        The 2D image from which to make Poisson noise.  Each pixel in the
        image must have a positive value (e.g., electron or photon
        counts).

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.

    Returns
    -------
    image : `~numpy.ndarray` or `~astropy.units.Quantity`
        The 2D image of Poisson noise.  The image is generated by
        drawing samples from a Poisson distribution with expectation
        values for each pixel given by the input ``image``.

    See Also
    --------
    make_noise_image, make_gaussian_sources, make_random_gaussians

    Examples
    --------

    .. plot::
        :include-source:

        # make a table of Gaussian sources
        from astropy.table import Table
        table = Table()
        table['amplitude'] = [50, 70, 150, 210]
        table['x_mean'] = [160, 25, 150, 90]
        table['y_mean'] = [70, 40, 25, 60]
        table['x_stddev'] = [15.2, 5.1, 3., 8.1]
        table['y_stddev'] = [2.6, 2.5, 3., 4.7]
        table['theta'] = np.array([145., 20., 0., 60.]) * np.pi / 180.

        # make an image of the sources and add a background level,
        # then make the Poisson noise image.
        from photutils.datasets import make_gaussian_sources
        from photutils.datasets import make_poisson_noise
        shape = (100, 200)
        bkgrd = 10.
        image1 = make_gaussian_sources(shape, table) + bkgrd
        image2 = make_poisson_noise(image1, random_state=12345)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
        ax1.imshow(image1, origin='lower', interpolation='nearest')
        ax2.imshow(image2, origin='lower', interpolation='nearest')
    """

    prng = check_random_state(random_state)
    if isinstance(image, u.Quantity):
        return prng.poisson(image.value) * image.unit
    else:
        return prng.poisson(image)


def make_gaussian_sources(image_shape, source_table, oversample=1, unit=None,
                          hdu=False, wcs=False, wcsheader=None):
    """
    Make an image containing 2D Gaussian sources.

    Parameters
    ----------
    image_shape : 2-tuple of int
        Shape of the output 2D image.

    source_table : `~astropy.table.Table`
        Table of parameters for the Gaussian sources.  Each row of the
        table corresponds to a Gaussian source whose parameters are
        defined by the column names.  The column names must include
        ``flux`` or ``amplitude``, ``x_mean``, ``y_mean``, ``x_stddev``,
        ``y_stddev``, and ``theta`` (see
        `~astropy.modeling.functional_models.Gaussian2D` for a
        description of most of these parameter names).  If both ``flux``
        and ``amplitude`` are present, then ``amplitude`` will be
        ignored.

    oversample : float, optional
        The sampling factor used to discretize the
        `~astropy.modeling.functional_models.Gaussian2D` models on a
        pixel grid.

        If the value is 1.0 (the default), then the models will be
        discretized by taking the value at the center of the pixel bin.
        Note that this method will not preserve the total flux of very
        small sources.

        Otherwise, the models will be discretized by taking the average
        over an oversampled grid.  The pixels will be oversampled by the
        ``oversample`` factor.

    unit : `~astropy.units.UnitBase` instance, str, optional
        An object that represents the unit desired for the output image.
        Must be an `~astropy.units.UnitBase` object or a string
        parseable by the `~astropy.units` package.

    hdu : bool, optional
        If `True` returns ``image`` as an `~astropy.io.fits.ImageHDU`
        object.  To include WCS information in the header, use the
        ``wcs`` and ``wcsheader`` inputs.  Otherwise the header will be
        minimal.  Default is `False`.

    wcs : bool, optional
        If `True` and ``hdu=True``, then a simple WCS will be included
        in the returned `~astropy.io.fits.ImageHDU` header.  Default is
        `False`.

    wcsheader : dict or `None`, optional
        If ``hdu`` and ``wcs`` are `True`, this dictionary is passed to
        `~astropy.wcs.WCS` to generate the returned
        `~astropy.io.fits.ImageHDU` header.

    Returns
    -------
    image : `~numpy.ndarray` or `~astropy.units.Quantity` or `~astropy.io.fits.ImageHDU`
        Image or `~astropy.io.fits.ImageHDU` containing 2D Gaussian
        sources.

    See Also
    --------
    make_random_gaussians, make_noise_image, make_poisson_noise

    Examples
    --------

    .. plot::
        :include-source:

        # make a table of Gaussian sources
        from astropy.table import Table
        table = Table()
        table['amplitude'] = [50, 70, 150, 210]
        table['x_mean'] = [160, 25, 150, 90]
        table['y_mean'] = [70, 40, 25, 60]
        table['x_stddev'] = [15.2, 5.1, 3., 8.1]
        table['y_stddev'] = [2.6, 2.5, 3., 4.7]
        table['theta'] = np.array([145., 20., 0., 60.]) * np.pi / 180.

        # make an image of the sources without noise, with Gaussian
        # noise, and with Poisson noise
        from photutils.datasets import make_gaussian_sources
        from photutils.datasets import make_noise_image
        shape = (100, 200)
        image1 = make_gaussian_sources(shape, table)
        image2 = image1 + make_noise_image(shape, type='gaussian', mean=5.,
                                           stddev=5.)
        image3 = image1 + make_noise_image(shape, type='poisson', mean=5.)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 12))
        ax1.imshow(image1, origin='lower', interpolation='nearest')
        ax2.imshow(image2, origin='lower', interpolation='nearest')
        ax3.imshow(image3, origin='lower', interpolation='nearest')
    """

    image = np.zeros(image_shape, dtype=np.float64)
    y, x = np.indices(image_shape)

    if 'flux' in source_table.colnames:
        amplitude = source_table['flux'] / (2. * np.pi *
                                            source_table['x_stddev'] *
                                            source_table['y_stddev'])
    elif 'amplitude' in source_table.colnames:
        amplitude = source_table['amplitude']
    else:
        raise ValueError('either "amplitude" or "flux" must be columns in '
                         'the input source_table')

    for i, source in enumerate(source_table):
        model = Gaussian2D(amplitude=amplitude[i], x_mean=source['x_mean'],
                           y_mean=source['y_mean'],
                           x_stddev=source['x_stddev'],
                           y_stddev=source['y_stddev'], theta=source['theta'])
        if oversample == 1:
            image += model(x, y)
        else:
            image += discretize_model(model, (0, image_shape[1]),
                                      (0, image_shape[0]), mode='oversample',
                                      factor=oversample)
    if unit is not None:
        image = u.Quantity(image, unit=unit)

    if wcs and not hdu:
        raise ValueError("wcs header only works with hdu output, use keyword "
                         "'hdu=True'")

    if hdu is True:
        from astropy.io import fits
        if wcs:
            from astropy.wcs import WCS
            if wcsheader is None:
                # Go with the simplest valid header
                header = WCS({'CTYPE1': 'RA---TAN',
                              'CTYPE2': 'DEC--TAN',
                              'CRPIX1': int(image_shape[1] / 2),
                              'CRPIX2': int(image_shape[0] / 2)}, ).to_header()
            else:
                header = WCS(wcsheader)
        else:
            header = None
        image = fits.ImageHDU(image, header=header)

    return image


def make_random_gaussians(n_sources, flux_range, xmean_range, ymean_range,
                          xstddev_range, ystddev_range, amplitude_range=None,
                          random_state=None):
    """
    Make a `~astropy.table.Table` containing parameters for randomly
    generated 2D Gaussian sources.

    Each row of the table corresponds to a Gaussian source whose
    parameters are defined by the column names.  The parameters are
    drawn from a uniform distribution over the specified input bounds.

    The output table can be input into `make_gaussian_sources` to create
    an image containing the 2D Gaussian sources.

    Parameters
    ----------
    n_sources : float
        The number of random Gaussian sources to generate.

    flux_range : array-like
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source fluxes.
        ``flux_range`` will be ignored if ``amplitude_range`` is input.

    xmean_range : array-like
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source ``x_mean``.

    ymean_range : array-like
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source ``y_mean``.

    xstddev_range : array-like
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source ``x_stddev``.

    ystddev_range : array-like
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source ``y_stddev``.

    amplitude_range : array-like, optional
        The lower and upper boundaries, ``(lower, upper)``, of the
        uniform distribution from which to draw source amplitudes.  If
        ``amplitude_range`` is input, then ``flux_range`` will be
        ignored.

    random_state : int or `~numpy.random.RandomState`, optional
        Pseudo-random number generator state used for random sampling.
        Separate function calls with the same parameters and
        ``random_state`` will generate the identical sources.

    Returns
    -------
    table : `~astropy.table.Table`
        A table of parameters for the randomly generated Gaussian
        sources.  Each row of the table corresponds to a Gaussian source
        whose parameters are defined by the column names.  The column
        names will include ``flux`` or ``amplitude``, ``x_mean``,
        ``y_mean``, ``x_stddev``, ``y_stddev``, and ``theta`` (see
        `~astropy.modeling.functional_models.Gaussian2D` for a
        description of most of these parameter names).

    See Also
    --------
    make_gaussian_sources, make_noise_image, make_poisson_noise

    Examples
    --------

    .. plot::
        :include-source:

        # create the random sources
        from photutils.datasets import make_random_gaussians
        n_sources = 100
        flux_range = [500, 1000]
        xmean_range = [0, 500]
        ymean_range = [0, 300]
        xstddev_range = [1, 5]
        ystddev_range = [1, 5]
        table = make_random_gaussians(n_sources, flux_range, xmean_range,
                                      ymean_range, xstddev_range,
                                      ystddev_range, random_state=12345)

        # make an image of the random sources without noise, with
        # Gaussian noise, and with Poisson noise
        from photutils.datasets import make_gaussian_sources
        from photutils.datasets import make_noise_image
        shape = (300, 500)
        image1 = make_gaussian_sources(shape, table)
        image2 = image1 + make_noise_image(shape, type='gaussian', mean=5.,
                                           stddev=2.)
        image3 = image1 + make_noise_image(shape, type='poisson', mean=5.)

        # plot the images
        import matplotlib.pyplot as plt
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 12))
        ax1.imshow(image1, origin='lower', interpolation='nearest')
        ax2.imshow(image2, origin='lower', interpolation='nearest')
        ax3.imshow(image3, origin='lower', interpolation='nearest')
    """

    prng = check_random_state(random_state)
    sources = Table()
    if amplitude_range is None:
        sources['flux'] = prng.uniform(flux_range[0], flux_range[1], n_sources)
    else:
        sources['amplitude'] = prng.uniform(amplitude_range[0],
                                            amplitude_range[1], n_sources)
    sources['x_mean'] = prng.uniform(xmean_range[0], xmean_range[1], n_sources)
    sources['y_mean'] = prng.uniform(ymean_range[0], ymean_range[1], n_sources)
    sources['x_stddev'] = prng.uniform(xstddev_range[0], xstddev_range[1],
                                       n_sources)
    sources['y_stddev'] = prng.uniform(ystddev_range[0], ystddev_range[1],
                                       n_sources)
    sources['theta'] = prng.uniform(0, 2.*np.pi, n_sources)
    return sources


def make_4gaussians_image(hdu=False, wcs=False, wcsheader=None):
    """
    Make an example image containing four 2D Gaussians plus Gaussian
    noise.

    The background has a mean and standard deviation of 5.

    Parameters
    ----------
    hdu : bool, optional
        If `True` returns ``image`` as an `~astropy.io.fits.ImageHDU`
        object.  To include WCS information in the header, use the
        ``wcs`` and ``wcsheader`` inputs.  Otherwise the header will be
        minimal.  Default is `False`.

    wcs : bool, optional
        If `True` and ``hdu=True``, then a simple WCS will be included
        in the returned `~astropy.io.fits.ImageHDU` header.  Default is
        `False`.

    wcsheader : dict or `None`, optional
        If ``hdu`` and ``wcs`` are `True`, this dictionary is passed to
        `~astropy.wcs.WCS` to generate the returned
        `~astropy.io.fits.ImageHDU` header.

    Returns
    -------
    image : `~numpy.ndarray` or `~astropy.io.fits.ImageHDU`
        Image or `~astropy.io.fits.ImageHDU` containing Gaussian
        sources.

    See Also
    --------
    make_100gaussians_image

    Examples
    --------
    .. plot::
        :include-source:

        from photutils import datasets
        image = datasets.make_4gaussians_image()
        plt.imshow(image, origin='lower', cmap='gray')
    """

    table = Table()
    table['amplitude'] = [50, 70, 150, 210]
    table['x_mean'] = [160, 25, 150, 90]
    table['y_mean'] = [70, 40, 25, 60]
    table['x_stddev'] = [15.2, 5.1, 3., 8.1]
    table['y_stddev'] = [2.6, 2.5, 3., 4.7]
    table['theta'] = np.array([145., 20., 0., 60.]) * np.pi / 180.
    shape = (100, 200)
    sources = make_gaussian_sources(shape, table, hdu=hdu,
                                    wcs=wcs, wcsheader=wcsheader)
    noise = make_noise_image(shape, type='gaussian', mean=5.,
                             stddev=5., random_state=12345)

    if hdu is True:
        sources.data += noise
        data = sources
    else:
        data = (sources + noise)

    return data


def make_100gaussians_image():
    """
    Make an example image containing 100 2D Gaussians plus Gaussian
    noise.

    The background has a mean of 5 and a standard deviation of 2.

    Returns
    -------
    image : `~numpy.ndarray`
        Image containing Gaussian sources.

    See Also
    --------
    make_4gaussians_image

    Examples
    --------
    .. plot::
        :include-source:

        from photutils import datasets
        image = datasets.make_100gaussians_image()
        plt.imshow(image, origin='lower', cmap='gray')
    """

    n_sources = 100
    flux_range = [500, 1000]
    xmean_range = [0, 500]
    ymean_range = [0, 300]
    xstddev_range = [1, 5]
    ystddev_range = [1, 5]
    table = make_random_gaussians(n_sources, flux_range, xmean_range,
                                  ymean_range, xstddev_range,
                                  ystddev_range, random_state=12345)
    shape = (300, 500)
    image1 = make_gaussian_sources(shape, table)
    image2 = image1 + make_noise_image(shape, type='gaussian', mean=5.,
                                       stddev=2., random_state=12345)
    return image2
