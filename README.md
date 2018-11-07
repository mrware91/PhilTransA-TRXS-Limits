# PhilTransA-TRXS-Limits
# Created by Matthew R. Ware
Philosopical Transaction A code base. On the limits of observing motion in time-resolved x-ray scattering.

# Use and installation for analyzing the Legendre projected data
This code base may be used on any computer to analyze the Legendre projected data, phil-trans-data.h5, using the FourierAnalysis notebook.
No installation is required beyond (1) Python2.7, (2) JupyterHub, and (3) standard libraries like numpy. 
Simply open the FourierAnalysis notebook, specify the installation directory in the first directory, then run each cell.

# Use and installation for analyzing the entire database
Upon request, we can provide access to the full database to analyze run 74 of xppl2816.
Installation requires moving src.bashrc to ~/.bashrc, as well as specifying the installation directory in each analysis notebook.
Following this, the data may be analyzed by running PointDataGrabber, CubeMaker, LegendreAnalysis, and FourierAnalysis in turn.
