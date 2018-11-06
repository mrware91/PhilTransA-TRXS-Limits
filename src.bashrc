#!/bin/bash
#echo -ne "\033]0;$(hostname)\007"
alias mysrc="source ~/.bashrc"
########################################################
##########~ DIFFUSE_TRXS_ANALYSIS variables             
########################################################
export PATH="$PATH:/reg/neh/home/mrware/XPP_WINTER_2018/Dynamical_PSANA_Wrapper_Class"
export DynamicPSANAPath="/reg/neh/home/mrware/XPP_WINTER_2018/Dynamical_PSANA_Wrapper_Class"

myhost=$(hostname)
#if [ "${myhost:0:5}" = "psana" ]; then
#
source /reg/g/psdm/etc/psconda.sh
#
#fi

#source /reg/g/psdm/etc/ana_env.sh
export PSPKG_ROOT=/reg/common/package
alias HDFVIEW=/reg/common/package/hdfview/2.9/x86_64-ubu12-gcc46-opt/bin/hdfview.sh
alias MATLAB=/reg/common/package/matlab/R2016a/bin/matlab
alias CHECKMATLAB='/reg/common/package/scripts/matlic --show-users'
########################################################
##########~ END              
########################################################
xppl2816=/reg/d/psdm/xpp/xppl2816
export PATH="$PATH:~/bin"

xppx29516=/reg/d/psdm/xpp/xppx29516
#export CodeDir=/reg/neh/home/mrware/XPP_WINTER_2018/xppl2816
#export CodeDir=/reg/neh/home/mrware/XPP_WINTER_2018/xppx29516
#export CodeDir=/reg/neh/home/mrware/XPP_WINTER_2018/xppx29516v2
