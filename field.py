#!/usr/bin/env/python
"""
Pyrate - Optical raytracing based on Python

Copyright (C) 2014 Moritz Esslinger moritz.esslinger@web.de
               and    Uwe Lippmann  uwe.lippmann@web.de

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

from numpy import *

def ChiefSlopeByObjectHeight(opticalSystem, ray, objFieldXY):
    """
    Calculates the chief ray slope from a object field height.

    :param opticalSystem: OpticalSystem object
    :param ray: raybundle object
    :param objFieldXY: object field height in x and y direction (1d numpy array of 2 floats)

    :return chiefSlopeXY: chief ray slope in x and y direction (1d numpy array of 2 floats)
    """
    
    zen, magen, zex, magex, abcd_obj_stop, abcd_stop_im = opticalSystem.getParaxialPupil(ray)
    chiefSlopeXY = - objFieldXY / zen
    return chiefSlopeXY


def ChiefSlopeByObjectChiefAngle(opticalSystem, ray, objChiefAngle):
    """
    Calculates the chief ray slope from the object sided chief ray angle.

    :param opticalSystem: OpticalSystem object
    :param ray: raybundle object
    :param objChiefAngle: object sided chief ray angle in degree (1d numpy array of 2 floats)

    :return chiefSlopeXY: chief ray slope in x and y direction (1d numpy array of 2 floats)
    """
    
    return tan( objChiefAngle * pi / 180. )


def ChiefSlopeByParaxialImageHeight(opticalSystem, ray, imFieldXY):
    """
    Calculates the chief ray slope from a object field height.

    :param opticalSystem: OpticalSystem object
    :param ray: raybundle object
    :param imFieldXY: image field height in x and y direction (1d numpy array of 2 floats)

    :return chiefSlopeXY: chief ray slope in x and y direction (1d numpy array of 2 floats)
    """
    
    zen, magen, zex, magex, abcd_obj_stop, abcd_stop_im = opticalSystem.getParaxialPupil(ray)
    pmag = opticalSystem.getParaxialMagnification(ray)        

    chiefSlopeXY = - imFieldXY / ( zen * pmag )
    return chiefSlopeXY


