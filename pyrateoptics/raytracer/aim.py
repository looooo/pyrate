#!/usr/bin/env/python
"""
Pyrate - Optical raytracing based on Python

Copyright (C) 2014-2018
               by     Moritz Esslinger moritz.esslinger@web.de
               and    Johannes Hartung j.hartung@gmx.net
               and    Uwe Lippmann  uwe.lippmann@web.de
               and    Thomas Heinze t.heinze@uni-jena.de
               and    others

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

import numpy as np

from pyrateoptics.core.log import BaseLogger
from pyrateoptics.raytracer.helpers import build_pilotbundle, build_pilotbundle_complex, choose_nearest
from pyrateoptics.raytracer.globalconstants import degree, standard_wavelength
from pyrateoptics.sampling2d.raster import RectGrid
from pyrateoptics.raytracer.ray import RayBundle, returnDtoK
from pyrateoptics.raytracer.helpers_math import rodrigues

class FieldManager(BaseLogger):
    pass

class Aimy(BaseLogger):

    """
    Should take care about ray aiming (approximatively and real).
    Should generate aiming matrices and raybundles according to
    aiming specifications and field specifications.
    """

    def __init__(self, s, seq,
                 wave=standard_wavelength,
                 num_pupil_points=100,
                 stopsize=10,
                 name="", kind="aimy", **kwargs):

        super(Aimy, self).__init__(name=name, kind=kind, **kwargs)
        self.field_raster = RectGrid()
        self.pupil_raster = RectGrid()
        self.stopsize = stopsize
        self.num_pupil_points = num_pupil_points
        self.wave = wave

        self.update(s, seq)

    def extractABCD(self, xyuv):

        self.info(str(xyuv.shape))

        Axyuv = xyuv[0:2, 0:2]
        Bxyuv = xyuv[0:2, 2:4]  # take only real part of the k vectors
        Cxyuv = xyuv[2:4, 0:2]
        Dxyuv = xyuv[2:4, 2:4]

        return (Axyuv, Bxyuv, Cxyuv, Dxyuv)

    def update(self, s, seq):

        obj_dx = 0.1            # pilot bundle properties
        obj_dphi = 1.*degree    # pilot bundle properties

        first_element_seq_name = seq[0]
        (first_element_name, first_element_seq) = first_element_seq_name
        (objsurfname, objsurfoptions) = first_element_seq[0]

        self.objectsurface = s.elements[first_element_name].surfaces[objsurfname]
        self.start_material = s.material_background
        # TODO: pilotray starts always in background (how about immersion?)
        # if mat is None: ....

        #build_pilotbundle(
        #    self.objectsurface,
        #    self.start_material,
        #    (obj_dx, obj_dx),
        #    (obj_dphi, obj_dphi),
        #    num_sampling_points=3) # TODO: wavelength?


        self.info("call complex sampled pilotbundle")
        pilotbundles = build_pilotbundle_complex(
            self.objectsurface,
            self.start_material,
            (obj_dx, obj_dx),
            (obj_dphi, obj_dphi),
            num_sampling_points=3)

        self.info("choose last raybundle (hard coded)")
        self.pilotbundle = pilotbundles[-1]
        # TODO: one solution selected hard coded

        (self.m_obj_stop, self.m_stop_img) = s.extractXYUV(self.pilotbundle, seq)

        self.info("show linear matrices")
        self.info(np.array_str(self.m_obj_stop, precision=5, suppress_small=True))
        self.info(np.array_str(self.m_stop_img, precision=5, suppress_small=True))


    def aim_core_angle_known(self, theta2d):
        """
        knows about xyuv matrices
        """

        (thetax, thetay) = theta2d

        rmx = rodrigues(thetax, [0, 1, 0])
        rmy = rodrigues(thetay, [1, 0, 0])
        rmfinal = np.dot(rmy, rmx)

        dpilot_global = self.pilotbundle.returnKtoD()[0, :, 0]
        kpilot_global = self.pilotbundle.k[0, :, 0]
        dpilot_object = self.objectsurface.rootcoordinatesystem.returnGlobalToLocalDirections(dpilot_global)[:, np.newaxis]
        kpilot_object = self.objectsurface.rootcoordinatesystem.returnGlobalToLocalDirections(kpilot_global)[:, np.newaxis]
        kpilot_object = np.repeat(kpilot_object, self.num_pupil_points, axis=1)
        d = np.dot(rmfinal, dpilot_object)

        k = returnDtoK(d) # TODO: implement fake implementation
        dk = k - kpilot_object
        dk_obj = dk[0:2, :]

        (A_obj_stop, B_obj_stop, C_obj_stop, D_obj_stop) = self.extractABCD(self.m_obj_stop)

        A_obj_stop_inv = np.linalg.inv(A_obj_stop)

        (xp, yp) = self.pupil_raster.getGrid(self.num_pupil_points)
        dr_stop = (np.vstack((xp, yp))*self.stopsize)

        intermediate = np.dot(B_obj_stop, dk_obj)
        dr_obj = np.dot(A_obj_stop_inv, dr_stop - intermediate)

        return (dr_obj, dk_obj)


    def aim_core_k_known(self, dk_obj):
        """
        knows about xyuv matrices
        """
        (A_obj_stop, B_obj_stop, C_obj_stop, D_obj_stop) = self.extractABCD(self.m_obj_stop)

        A_obj_stop_inv = np.linalg.inv(A_obj_stop)


        (xp, yp) = self.pupil_raster.getGrid(self.num_pupil_points)
        dr_stop = (np.vstack((xp, yp))*self.stopsize)

        dk_obj2 = np.repeat(dk_obj[:, np.newaxis], self.num_pupil_points, axis=1)


        intermediate = np.dot(B_obj_stop, dk_obj2)
        dr_obj = np.dot(A_obj_stop_inv, dr_stop - intermediate)

        return (dr_obj, dk_obj2)

    def aim_core_r_known(self, delta_xy):

        (A_obj_stop,
         B_obj_stop,
         C_obj_stop,
         D_obj_stop) = self.extractABCD(self.m_obj_stop)

        self.info(str(B_obj_stop.shape))

        B_obj_stop_inv = np.linalg.inv(B_obj_stop)

        (xp, yp) = self.pupil_raster.getGrid(self.num_pupil_points)
        dr_stop = (np.vstack((xp, yp))*self.stopsize)

        dr_obj = np.repeat(delta_xy[:, np.newaxis], self.num_pupil_points, axis=1)
        dk_obj = np.dot(B_obj_stop_inv, dr_stop - np.dot(A_obj_stop, dr_obj))

        # TODO: in general some direction vector is derived
        # TODO: this must been mapped to a k vector

        # TODO: what about anamorphic systems?

        return (dr_obj, dk_obj)

    def aim(self, delta_xy, fieldtype="angle"):
        """
        Generates bundles.
        """

        if fieldtype == "angle":
            (dr_obj, dk_obj) = self.aim_core_angle_known(delta_xy)
        elif fieldtype == "objectheight":
            (dr_obj, dk_obj) = self.aim_core_r_known(delta_xy)
        elif fieldtype == "kvector":
            # (dr_obj, dk_obj) = self.aim_core_k_known(delta_xy)
            raise NotImplementedError()
        else:
            raise NotImplementedError()

        (dim, num_points) = np.shape(dr_obj)

        dr_obj3d = np.vstack((dr_obj, np.zeros(num_points)))
        dk_obj3d = np.vstack((dk_obj, np.zeros(num_points)))

        xp_objsurf = self.objectsurface.rootcoordinatesystem.returnGlobalToLocalPoints(self.pilotbundle.x[0, :, 0])
        xp_objsurf = np.repeat(xp_objsurf[:, np.newaxis], num_points, axis=1)
        dx3d = np.dot(self.objectsurface.rootcoordinatesystem.localbasis.T, dr_obj3d)
        xparabasal = xp_objsurf + dx3d

        kp_objsurf = self.objectsurface.rootcoordinatesystem.returnGlobalToLocalDirections(self.pilotbundle.k[0, :, 0])
        kp_objsurf = np.repeat(kp_objsurf[:, np.newaxis], num_points, axis=1)
        dk3d = np.dot(self.objectsurface.rootcoordinatesystem.localbasis.T, dk_obj3d)
        # TODO: k coordinate system for which dispersion relation is respected

        kparabasal = kp_objsurf + dk3d
        E_obj = self.pilotbundle.Efield[0, :, 0]
        Eparabasal = np.repeat(E_obj[:, np.newaxis], num_points, axis=1)


        # Aimy: returns only linearized results which are not exact
        return RayBundle(xparabasal, kparabasal, Eparabasal, wave=self.wave)