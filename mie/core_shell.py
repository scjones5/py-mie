
import numpy as np

from ._mie import core_shell_module 

#: Density of pure water, in kg/m^3
RHO_WATER = 1e3

def particle_scatter(particle_radius, core_fraction, radiation_lambda,
                     n_shell, n_core):
    """ Compute the scattering/absorption efficiency and asymmetry
    parameter for a heterogeneous, core-shell mixed particle.

    This function interfaces with the compiled Mie theory modules in order
    to determine the scattering parameters.

    Parameters
    ----------
    particle_radius : float
        The total particle radius (core + shell) in microns
    core_fraction : float
        The fraction of the particle comprised by its core, 0.0-1.0
    radiation_lambda : float
        Wavelength of incident radiation in microns
    n_shell, n_core : complex
        Complex refractive indices of the shell, and core respectively

    Returns
    -------
    Qsca, Qabs, asym : floats
        The scattering efficiency, absorption efficiency, and asymmetry
        parameter for the specified particle

    """ 

    ## Pass directly to Mie module
    Qsca0, Qext0, asym0 = core_shell_module.core_shell_mie( \
        particle_radius, 
        core_fraction*particle_radius,
        n_shell,
        n_core,
        radiation_lambda
    )

    ## Post-process to properly set scattering and absorption efficiencies
    Qsca = np.min([Qsca0, Qext0]) # scattering efficiency
    Qabs = Qext0 - Qsca           # absorption efficiency
    asym = asym0

    return Qsca, Qabs, asym

def integrate_mode(core_fraction, n_shell, n_core, radiation_lambda,
                   mode_radius, mode_sigma,
                   r_min=1e-3, r_max=100., nr=200):
    """ Integrate Mie theory calculations over a lognormal aerosol mode with
    homogeneous particle properties, weighting by size distribution.

    Parameters
    ----------
    core_fraction : float
        The fraction of the particle comprised by its core, 0.0-1.0
    n_shell, n_core : complex
        Complex refractive indices of the shell, and core respectively
    radiation_lambda : float
        Wavelength of incident radiation in microns
    mode_radius : float
        The geometric mean or mode radius of the aerosol size distribution, in
        microns
    mode_sigma : float
        The geometric standard deviation of the aerosol size distribution
    r_min, r_max : float (optional)
        The minimum and maximum particle radii to use in the integration, in 
        microns
    nr : int (optional)
        The number of particle radii to use in the integration

    Returns
    -------
    mie_sca, mie_abs, mie_asym : floats
        Scattering efficiency, absorption efficiency, and asymmetry parameter
        integrated over an aerosol size distribution

    """

    ## Generate the integration grid for the particle size distribution
    dlogr = np.log(r_max/r_min)/(nr-1)
    logr = [np.log(r_min), ]
    for i in xrange(1, nr):
        logr.append(logr[-1] + dlogr)
    radii = np.exp(logr)

    sumsca  = 0.0
    sumabs  = 0.0
    sumg    = 0.0
    volwet  = 0.0
    volcore = 0.0    

    ## Integration loop
    for i, radius in enumerate(radii):

        ## Mie theory calculation
        Qsca, Qabs, asym = particle_scatter( \
            radius, core_fraction, radiation_lambda, n_shell, n_core
        )

        ## Compute weights and volumes for integral sum
        exparg   = np.log(radius / mode_radius)/np.log(mode_sigma)
        dsdlogr  = np.exp(-0.5*exparg**2) # m^2/m3(air)] log-normal cross section area
        volwet  += (4./3.)*(radius*1e-6)*dsdlogr*dlogr # [m3/m3(air)] wet volume
        volcore += (4./3.)*(core_fraction**3)*(radius*1e-6)*dsdlogr*dlogr 

        sumabs += Qabs*dsdlogr*dlogr # [m^2/m3(air)] absorption cross-section
        sumsca += Qsca*dsdlogr*dlogr # [m^2/m3(air)] scattering cross-section
        sumg   += asym*Qsca*dsdlogr*dlogr

    mie_sca  = np.max([sumsca, 0.]) / (volwet * RHO_WATER) # [m^2/kg] specific scattering cross-section
    mie_abs  = np.max([sumabs, 0.]) / (volwet * RHO_WATER) # [m^2/kg] specific absorption cross-section
    mie_asym =                 sumg / sumsca               # average asymmetry 

    return mie_sca, mie_abs, mie_asym