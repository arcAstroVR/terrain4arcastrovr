# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Terrain4arcastrovr
								 A QGIS plugin
 Outputs 300km square terrain data for arcAstroVR
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
							  -------------------
		begin				: 2021-11-17
		git sha			  : $Format:%H$
		copyright			: (C) 2021 by Kuninori Iwashiro (scienceNODE)
		email				: iwashiro@science-node.com
 ***************************************************************************/

/***************************************************************************
 *																		 *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or	 *
 *   (at your option) any later version.								   *
 *																		 *
 ***************************************************************************/
"""
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .terrain4arcastrovr_dialog import Terrain4arcastrovrDialog
import os, sys, time, datetime
import processing
import numpy as np
from osgeo import gdal


class Terrain4arcastrovr:
	"""QGIS Plugin Implementation."""

	def __init__(self, iface):
		"""Constructor.

		:param iface: An interface instance that will be passed to this class
			which provides the hook by which you can manipulate the QGIS
			application at run time.
		:type iface: QgsInterface
		"""
		# Save reference to the QGIS interface
		self.iface = iface
		# initialize plugin directory
		self.plugin_dir = os.path.dirname(__file__)
		# initialize locale
		locale = QSettings().value('locale/userLocale')[0:2]
		locale_path = os.path.join(
			self.plugin_dir,
			'i18n',
			'Terrain4arcastrovr_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)
			QCoreApplication.installTranslator(self.translator)

		# Declare instance attributes
		self.actions = []
		self.menu = self.tr(u'&Terrain maker for arcAstroVR')

		# Check if plugin was started the first time in current QGIS session
		# Must be set in initGui() to survive plugin reloads
		self.first_start = None

	# noinspection PyMethodMayBeStatic
	def tr(self, message):
		"""Get the translation for a string using Qt translation API.

		We implement this ourselves since we do not inherit QObject.

		:param message: String for translation.
		:type message: str, QString

		:returns: Translated version of message.
		:rtype: QString
		"""
		# noinspection PyTypeChecker,PyArgumentList,PyCallByClass
		return QCoreApplication.translate('Terrain4arcastrovr', message)


	def add_action(
		self,
		icon_path,
		text,
		callback,
		enabled_flag=True,
		add_to_menu=True,
		add_to_toolbar=True,
		status_tip=None,
		whats_this=None,
		parent=None):
		"""Add a toolbar icon to the toolbar.

		:param icon_path: Path to the icon for this action. Can be a resource
			path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
		:type icon_path: str

		:param text: Text that should be shown in menu items for this action.
		:type text: str

		:param callback: Function to be called when the action is triggered.
		:type callback: function

		:param enabled_flag: A flag indicating if the action should be enabled
			by default. Defaults to True.
		:type enabled_flag: bool

		:param add_to_menu: Flag indicating whether the action should also
			be added to the menu. Defaults to True.
		:type add_to_menu: bool

		:param add_to_toolbar: Flag indicating whether the action should also
			be added to the toolbar. Defaults to True.
		:type add_to_toolbar: bool

		:param status_tip: Optional text to show in a popup when mouse pointer
			hovers over the action.
		:type status_tip: str

		:param parent: Parent widget for the new action. Defaults None.
		:type parent: QWidget

		:param whats_this: Optional text to show in the status bar when the
			mouse pointer hovers over the action.

		:returns: The action that was created. Note that the action is also
			added to self.actions list.
		:rtype: QAction
		"""

		icon = QIcon(icon_path)
		action = QAction(icon, text, parent)
		action.triggered.connect(callback)
		action.setEnabled(enabled_flag)

		if status_tip is not None:
			action.setStatusTip(status_tip)

		if whats_this is not None:
			action.setWhatsThis(whats_this)

		if add_to_toolbar:
			# Adds plugin icon to Plugins toolbar
			self.iface.addToolBarIcon(action)

		if add_to_menu:
			self.iface.addPluginToMenu(
				self.menu,
				action)

		self.actions.append(action)

		return action

	def initGui(self):
		"""Create the menu entries and toolbar icons inside the QGIS GUI."""

		icon_path = ':/plugins/terrain4arcastrovr/icon.png'
		self.add_action(
			icon_path,
			text=self.tr(u'Terrain4arcAstroVR'),
			callback=self.run,
			parent=self.iface.mainWindow())

		# will be set False in run()
		self.first_start = True


	def unload(self):
		"""Removes the plugin menu item and icon from QGIS GUI."""
		for action in self.actions:
			self.iface.removePluginMenu(
				self.tr(u'&Terrain maker for arcAstroVR'),
				action)
			self.iface.removeToolBarIcon(action)

	def run(self):
		"""Run method that performs all the real work"""

		# Create the dialog with elements (after translation) and keep reference
		# Only create GUI ONCE in callback, so that it will only load when the plugin is started
		if self.first_start == True:
			self.first_start = False
			self.dlg = Terrain4arcastrovrDialog()

		# PREPARE lineEdit
		self.dlg.lineEdit1_1.clear()

		# PREPARE COMBO BOX
		self.dlg.comboBox2_1.clear()
		self.dlg.comboBox2_2.clear()
		self.dlg.comboBox2_3.clear()
		self.dlg.comboBox3_1.clear()
		self.dlg.comboBox3_2.clear()
		self.dlg.comboBox3_3.clear()
		self.dlg.comboBox4.clear()
		self.layers = [layer for layer in QgsProject.instance().mapLayers().values()]
		self.single_list = []
		self.single_list.append("")
		self.multi_list = []
		self.multi_list.append("")
		self.vector_list = []
		self.vector_list.append("")
		for layer in self.layers :
			if layer.type() == QgsMapLayer.VectorLayer:
				if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
					self.vector_list.append(layer.name())
			elif (layer.type() == QgsMapLayer.RasterLayer) and (layer.name() !="areaTerrain_DTM") and (layer.name() !="areaTerrain_TEX") and (layer.name() !="baseTerrain_DTM") and (layer.name() !="baseTerrain_TEX"):
				if layer.rasterType() <2:
					self.single_list.append(layer.name())
				else:
					self.multi_list.append(layer.name())
		self.dlg.comboBox2_1.addItems(self.single_list)
		self.dlg.comboBox2_2.addItems(self.single_list)
		self.dlg.comboBox2_3.addItems(self.multi_list)
		self.dlg.comboBox3_1.addItems(self.single_list)
		self.dlg.comboBox3_2.addItems(self.single_list)
		self.dlg.comboBox3_3.addItems(self.multi_list)
		self.dlg.comboBox4.addItems(self.vector_list)

		# comboBox???????????????????????????
		self.dlg.comboBox2_1.currentIndexChanged.connect(self.combobox2Activated) 
		self.dlg.comboBox3_1.currentIndexChanged.connect(self.combobox3Activated) 

		# PREPARE SAVE Dir
		self.dlg.mQgsFileWidget_outputPath.setFilePath(os.path.expanduser('~/Desktop'))
		self.dlg.mQgsFileWidget_outputPath.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
		self.dlg.mQgsFileWidget_outputPath.setDialogTitle("???????????????????????????????????????????????????")

		# doubleSpinBox???????????????????????????
		self.dlg.doubleSpinBox.valueChanged.connect(self.spinboxActivated) 

		# show the dialog
		self.dlg.show()

		# Run the dialog event loop
		result = self.dlg.exec_()
		# See if OK was pressed
		if result:
			# Do something useful here - delete the line containing pass and
			# substitute with your code.
			self.main()
			pass

	#???????????????????????????????????????
	def combobox2Activated(self):
		if self.dlg.comboBox2_1.currentIndex() != 0:
			self.dlg.label2_2.setEnabled(True)
			self.dlg.label2_3.setEnabled(True)
			self.dlg.comboBox2_2.setEnabled(True)
			self.dlg.comboBox2_3.setEnabled(True)
		else:
			self.dlg.label2_2.setEnabled(False)
			self.dlg.label2_3.setEnabled(False)
			self.dlg.comboBox2_2.setEnabled(False)
			self.dlg.comboBox2_3.setEnabled(False)

	def combobox3Activated(self):
		if self.dlg.comboBox3_1.currentIndex() != 0:
			self.dlg.label3_2.setEnabled(True)
			self.dlg.label3_3.setEnabled(True)
			self.dlg.label3_4.setEnabled(True)
			self.dlg.label3_5.setEnabled(True)
			self.dlg.comboBox3_2.setEnabled(True)
			self.dlg.comboBox3_3.setEnabled(True)
			self.dlg.doubleSpinBox.setEnabled(True)
		else:
			self.dlg.label3_2.setEnabled(False)
			self.dlg.label3_3.setEnabled(False)
			self.dlg.label3_4.setEnabled(False)
			self.dlg.label3_5.setEnabled(False)
			self.dlg.comboBox3_2.setEnabled(False)
			self.dlg.comboBox3_3.setEnabled(False)
			self.dlg.doubleSpinBox.setEnabled(False)

	def spinboxActivated(self):
		area = self.dlg.doubleSpinBox.value() * 1024
		self.dlg.label3_5.setText("??????????????????"+ str('{:.1f}'.format(area)) +"m???")

	#???????????????????????????
	def isfloat(self, parameter):
		if not parameter.isdecimal():
			try:
				float(parameter)
				return True
			except ValueError:
				return False
		else:
			return True

	#BLH (lat, lon, ht) -> ECEF ??????(x, y, z)
	def blh2ecef(self, lat, lon, ht):
		lat_rad = np.deg2rad(lat)
		lon_rad = np.deg2rad(lon)
		n = lambda x: self.A / np.sqrt(1.0 - self.E2 * np.sin(np.deg2rad(x))**2)
		x = (n(lat) + ht) * np.cos(lat_rad) * np.cos(lon_rad)
		y = (n(lat) + ht) * np.cos(lat_rad) * np.sin(lon_rad)
		z = (n(lat) * (1.0 - self.E2) + ht) * np.sin(lat_rad)
		return [x, y, z]
	
	#ECEF ??????(x, y, z) -> BLH (lat, lon, ht) 
	def ecef2blh(self, x, y, z):
		n = lambda x: self.A / np.sqrt(1.0 - self.E2 * np.sin(np.deg2rad(x))**2)
		p = np.sqrt(x * x + y * y)
		theta = np.arctan2(z * self.A, p * self.B)
		lat = np.rad2deg(np.arctan2( z + self.ED2 * self.B * np.sin(theta)**3, p - self.E2 * self.A * np.cos(theta)**3))
		lon = np.rad2deg(np.arctan2(y, x))
		ht = (p / np.cos(np.deg2rad(lat))) - n(lat)
		return [lat, lon, ht]
	
	# y ??????????????????????????????
	def mat_y(self, ang):
		a = np.deg2rad(ang)
		c = np.cos(a)
		s = np.sin(a)
		return np.array([[c, 0.0, -s],[ 0.0, 1.0, 0.0],[ s, 0.0, c]])
	
	# z ??????????????????????????????
	def mat_z(self, ang):
		a = np.deg2rad(ang)
		c = np.cos(a)
		s = np.sin(a)
		return np.array([[ c, s, 0.0],[ -s, c, 0.0],[0.0, 0.0, 1.0]])
	
	# jpg??????
	def saveimg(self, options, path):
		render = QgsMapRendererParallelJob(options)
		render.start()
		render.waitForFinished()
		img = render.renderedImage()
		img.save(path, "jpg")
	
	def terainCalc(self, width, dem_mesh, dem_layer, geo_layer, mask_layer, mask_array, out_name):
		#????????????(m)???unity???Terrain??????????????????????????????+1px??????????????????????????????
		area_rect = '-'+str(int(width/2))+','+str(int(width/2+dem_mesh))+',-'+str(int(width/2+dem_mesh))+','+str(int(width/2))

		layer = QgsProject.instance().mapLayersByName(dem_layer)[0]
		uri = layer.dataProvider().dataSourceUri()
		#Mask??????
		if(out_name != "baseTerrain_DTM")and(mask_layer !=""):
			#DTM????????????????????????????????????
			parameter = { 'BANDS' : [1], 'DATA_TYPE' : 5, 'INPUT' : uri, 'OPTIONS' : '', 'OUTPUT' : 'TEMPORARY_OUTPUT' }
			memory_uri =  processing.run('gdal:rearrange_bands', parameter)
	
			#Mask _Lyer?????????????????????
			layer = QgsProject.instance().mapLayersByName(mask_layer)[0]
			parameter = { 'ADD' : True, 'BURN' : -self.down, 'EXTRA' : '', 'INPUT' : layer, 'INPUT_RASTER' : memory_uri['OUTPUT'], 'OUTPUT' : 'TEMPORARY_OUTPUT' }
			memory_uri = processing.run('gdal:rasterize_over_fixed_value', parameter)
			
			parameter ={'INPUT' : memory_uri['OUTPUT'], 'OUTPUT' : 'TEMPORARY_OUTPUT', 'TARGET_CRS' : self.crs, 'TARGET_RESOLUTION' : dem_mesh ,'TARGET_EXTENT' : area_rect, 'TARGET_EXTENT_CRS' : self.crs }
		else:
			parameter ={'INPUT' : uri, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'TARGET_CRS' : self.crs, 'TARGET_RESOLUTION' : dem_mesh ,'TARGET_EXTENT' : area_rect, 'TARGET_EXTENT_CRS' : self.crs }
		#DTM?????????????????????????????????????????????????????????
		dem = processing.run('gdal:warpreproject', parameter)
		#self.iface.addRasterLayer(dem['OUTPUT'], 'orthoDEM')

		#DTM???numpy??????????????????
		src = gdal.Open(dem['OUTPUT'], gdal.GA_ReadOnly)
		dem_array = src.GetRasterBand(1).ReadAsArray()
		dem_array[dem_array < 0] = 0

		if(geo_layer != ""):
			#GEOID?????????????????????????????????????????????????????????
			layer = QgsProject.instance().mapLayersByName(geo_layer)[0]
			uri = layer.dataProvider().dataSourceUri()
			parameter ={'INPUT' : uri, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'TARGET_CRS' : self.crs, 'TARGET_RESOLUTION' : dem_mesh ,'TARGET_EXTENT' : area_rect, 'TARGET_EXTENT_CRS' : self.crs }
			geo = processing.run('gdal:warpreproject', parameter)
			#self.iface.addRasterLayer(geo['OUTPUT'], 'orthoGEO')

			#GEOID???numpy??????????????????
			src = gdal.Open(geo['OUTPUT'], gdal.GA_ReadOnly)
			geo_array = src.GetRasterBand(1).ReadAsArray()
			geo_array[geo_array < 0] = 0

			#DTM/GEOID???????????????
			out_array = dem_array + geo_array
		else:
			print(out_name+" does not set GEOID")
			out_array = dem_array
	
		#??????????????????????????????
		progressMessageBar = iface.messageBar().createMessage("Calculate DTM: "+dem_layer)
		self.progress = QProgressBar()
		self.progress.setMaximum(100)
		self.progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
		progressMessageBar.layout().addWidget(self.progress)
		self.iface.messageBar().pushWidget(progressMessageBar, Qgis.Info)

		#????????????????????????
		half_width = width/2
		px_size = width/dem_mesh
		plus_px_size = int(px_size +1)
		half_px_size = px_size / 2
		co_prog = 100/plus_px_size
		co_level = 65536/self.h_max
		mask = False
		if type(mask_array).__module__ == "numpy": 
			mask = True
			mask_w = int(mask_array.shape[0]/2)
		for h in range(0, plus_px_size):
			QApplication.processEvents()
			self.progress.setValue(h*co_prog+1)
			for w in range(0, plus_px_size):
				z = out_array[w,h]
				ecef_t = np.dot(self.mat, [w*dem_mesh - half_width, h*dem_mesh - half_width, 0])
				ecef = np.add(self.ecef_o, ecef_t)
				blh = self.ecef2blh(*ecef)
				level = (z-blh[2]+self.zoffset)*co_level
				if mask: #???????????????????????????????????????
					center_x = int(w - half_px_size)
					center_y = int(h - half_px_size)
					if abs(center_x) < mask_w and abs(center_y) < mask_w:
						mask_z = mask_array[int(center_x+mask_w),int(center_y+mask_w)]
						if mask_z != 0:	#???????????????0????????????????????????????????????
							level = mask_z - self.down
				else:
					if out_name == "areaTerrain_DTM" and dem_array[w,h] == 0:	#?????????????????????0???????????????????????????0???????????????
						level = 0
				if level < 0:
						level = 0
				out_array[w,h] = level

		#?????????????????????????????????
		self.iface.messageBar().clearWidgets()

		#geotiff????????????
		geotransform = src.GetGeoTransform()
		originY = geotransform[3]
		originX = geotransform[0]
		dst = self.output_path + out_name+".tif"
		dtype = gdal.GDT_UInt16	# others: gdal.GDT_Byte, ...
		band = 1					# ????????????
		dst_raster = gdal.GetDriverByName('GTiff').Create(dst, int(px_size+1), int(px_size+1), band, dtype)
		dst_raster.SetGeoTransform((originX, dem_mesh, 0, originY, 0, -dem_mesh))
		dst_band = dst_raster.GetRasterBand(1)
		dst_band.WriteArray(out_array)
		dst_band.FlushCache()
		dst_raster = None
		
		#??????????????????
		layertree = QgsProject.instance().layerTreeRoot()
		try:
			layer = QgsProject.instance().mapLayersByName(out_name)[0]
		except IndexError:
			pass
		else:
			QgsProject.instance().removeMapLayer(layer)
		layer = self.iface.addRasterLayer(dst, out_name)
		layer.setCrs(self.crs)
	
		return out_array, dst
	
	def textureCalc(self, width, tex_mesh, tex_layer, out_name):
		#????????????(m)
		area_rect = '-'+str(int(width/2))+','+str(int(width/2))+',-'+str(int(width/2))+','+str(int(width/2))
	
		#TEXTURE???Canvas??????????????????xyz???????????????????????????????????????
		layer = QgsProject.instance().mapLayersByName(tex_layer)[0]
		uri = layer.dataProvider().dataSourceUri()
		parameter = { 'EXTENT' : area_rect, 'LAYERS' : [uri], 'MAP_UNITS_PER_PIXEL' : tex_mesh, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'TILE_SIZE' : width/tex_mesh }
		tex = processing.run('qgis:rasterize', parameter)
		layertree = QgsProject.instance().layerTreeRoot()
		try:
			layer = QgsProject.instance().mapLayersByName(out_name)[0]
		except IndexError:
			pass
		else:
			QgsProject.instance().removeMapLayer(layer)
		layer = self.iface.addRasterLayer(tex['OUTPUT'], out_name)
		layer.setCrs(self.crs)
	
	def main(self):
		# ???????????????????????????
		L_dem_layer = ""
		L_geo_layer = ""
		L_tex_layer = ""
		S_dem_layer = ""
		S_geo_layer = ""
		S_tex_layer = ""
		mask_layer = ""
		
		# ????????????????????????
		center_str = self.dlg.lineEdit1_1.text().split(",")
		if len(center_str) == 2:
			if self.isfloat(center_str[0]) and self.isfloat(center_str[1]):
				lat = float(center_str[0])	#??????
				lon = float(center_str[1])	#??????
			else:
				QMessageBox.information(None, '?????????', u'???????????????????????????????????????Err code1')
				return
		else: #MapCanvas??????????????????????????????
			if (center_str[0] != "") or len(center_str) > 2:
				QMessageBox.information(None, '?????????', u'???????????????????????????????????????Err code2')
				return
			center = self.iface.mapCanvas().center()
			canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
			epsg4326_crs = QgsCoordinateReferenceSystem(4326)
			crs_trans = QgsCoordinateTransform(canvas_crs, epsg4326_crs, QgsProject.instance())
			pt4326 = crs_trans.transform(center)
			lat = float(pt4326.y())	#??????
			lon = float(pt4326.x())	#??????
		if (lat < -90) or (lat > 90) or (lon < -180) or (lon >180):
			QMessageBox.information(None, '?????????', u'???????????????????????????????????????Err code3')
		else:
			print("?????????????????????,?????????="+str(lat)+", "+str(lon))
		
		self.output_path = self.dlg.mQgsFileWidget_outputPath.filePath()+"/"
		if self.output_path == "/":
			QMessageBox.information(None, '?????????', u'??????????????????????????????Err code4')
			return
		else:
			print("?????????="+self.output_path)

		#?????????????????????L_????????????????????????S_?????????????????????
		L_dem_layer = self.single_list[self.dlg.comboBox2_1.currentIndex()]
		L_geo_layer = self.single_list[self.dlg.comboBox2_2.currentIndex()]
		L_tex_layer = self.multi_list[self.dlg.comboBox2_3.currentIndex()]
		S_dem_layer = self.single_list[self.dlg.comboBox3_1.currentIndex()]
		S_geo_layer = self.single_list[self.dlg.comboBox3_2.currentIndex()]
		S_tex_layer = self.multi_list[self.dlg.comboBox3_3.currentIndex()]
		mask_layer = self.vector_list[self.dlg.comboBox4.currentIndex()]
		print("????????????????????????="+L_dem_layer+", "+L_geo_layer+", "+L_tex_layer)
		print("?????????????????????="+S_dem_layer+", "+S_geo_layer+", "+S_tex_layer)
		print("??????????????????="+mask_layer)
		
		if (self.dlg.comboBox2_1.currentIndex() == 0)and(self.dlg.comboBox3_1.currentIndex() == 0):
			QMessageBox.information(None, '?????????', u'DEM??????????????????????????????Err code5')
			return

		#???????????????output_size????????????(m)???dem_mesh???Terrain????????????(m)???tex_mesh???Texture???????????????m??????
		#Unity??????Terrain?????????(dem_px)???32,64,128,256,1024,2048,4096px??????????????????????????????????????????????????????
		#???????????????????????????????????????(dem_px)??????????????????????????????????????????(output_size)??????????????????????????????????????????????????????????????????????????????????????????
		L_output_size = 300000
		L_dem_px = 4096*3		#?????????????????????????????????256*3??????????????????????????????4096*3
		L_dem_mesh = L_output_size/L_dem_px
		L_tex_mesh = L_dem_mesh
		S_dem_px = 1024	#?????????????????????????????????128??????????????????????????????1024
		S_dem_mesh = self.dlg.doubleSpinBox.value()
		S_output_size = S_dem_px * S_dem_mesh
		S_tex_mesh = S_dem_mesh/10
		print("?????????="+str(S_dem_mesh)+", area="+str(S_output_size))

		#UnityTerrain??????????????????zoffset???????????????????????????h_max??????????????????m???????????????down?????????????????????????????????????????????m?????????????????????
		#h_max = 10000???zoffset=1000????????????????????????????????????????????????
		#??????-1000m???GeoTiff=0???Unity Box=0
		#??????0m???GeoTiif=6553.6???Unity Box=1000
		#??????9000m???GeoTiff=65536???Unity Box=10000
		self.zoffset = 1000
		self.h_max = 10000
		self.down = 10

		#????????????
		eqEarth=1.156							#???????????????????????????
		self.A = 6378137.0*eqEarth					# a(????????????????????????(?????????????????????))
		ONE_F = 298.257223563					# 1 / f(????????????????????????=(a - b) / a)
		self.B = self.A * (1.0 - 1.0 / ONE_F)					# b(????????????????????????)
		self.E2 = (1.0 / ONE_F) * (2 - (1.0 / ONE_F))		# e^2 = 2 * f - f * f = (a^2 - b^2) / a^2
		self.ED2    = self.E2 * self.A * self.A / (self.B * self.B)					# e'^2= (a^2 - b^2) / b^2

		#??????????????????
		start = time.time()
		print("????????????="+str(datetime.datetime.now()))
		
		#?????????????????????????????????????????????CRS????????????
		self.crs = QgsCoordinateReferenceSystem().fromProj4('+proj=ortho +lat_0='+str(lat)+' +lon_0='+str(lon)+' +x_0=0 +y_0=0 +ellps=sphere +units=m +no_defs')
		QgsProject.instance().setCrs(self.crs)
		
		#ERN->ECEF?????????????????????
		mat_0 = self.mat_z(-90.0)
		mat_1 = self.mat_y(lat-90.0)
		mat_2 = self.mat_z(-lon)
		self.mat = np.dot(np.dot(mat_2,mat_1),mat_0)
		
		#?????????ECEF?????????
		self.ecef_o = self.blh2ecef(lat, lon, 0)

		#?????????????????????++++++++++++++++++
		if(S_dem_layer != ""):
			#Terrain??????
			S_out, S_uri = self.terainCalc(S_output_size, S_dem_mesh, S_dem_layer, S_geo_layer, mask_layer, 0, "areaTerrain_DTM")
			#raw??????(?????????????????????????????????"<" ????????????16?????????"u2") https://note.nkmk.me/python-numpy-dtype-astype/
			S_out.astype('<u2').tofile(self.output_path+"terrain00.raw")
			
			if(S_tex_layer !=""):
				#Texture??????
				self.textureCalc(S_output_size, S_tex_mesh, S_tex_layer, "areaTerrain_TEX")
				texlayer = QgsProject.instance().mapLayersByName("areaTerrain_TEX")[0]
				options = QgsMapSettings()
				options.setLayers([texlayer])
				options.setBackgroundColor(QColor(0, 0, 0))
				options.setOutputSize(QSize(S_output_size/S_tex_mesh, S_output_size/S_tex_mesh))
				options.setExtent(QgsRectangle(-S_output_size/2, S_output_size/2, S_output_size/2, -S_output_size/2))
				self.saveimg(options, self.output_path+"terrain00.jpg")
			
			#Terrain Mask???Array??????
			s_width = str(int(S_output_size/2))
			area_rect = '-'+s_width+','+s_width+',-'+s_width+','+s_width
			
			#??????????????????????????? 'RESAMPLING' : 8??????????????????????????????????????????????????????????????????
			uri = S_uri
			parameter ={'INPUT' : uri, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'RESAMPLING' : 8, 'TARGET_CRS' : self.crs, 'TARGET_RESOLUTION' : L_dem_mesh ,'TARGET_EXTENT' : area_rect, 'TARGET_EXTENT_CRS' : self.crs }
			mask = processing.run('gdal:warpreproject', parameter)
			#iface.addRasterLayer(mask['OUTPUT'], 'areaTerrain_MASK')
			#areaTerrain_MASK???numpy??????????????????
			src = gdal.Open(mask['OUTPUT'], gdal.GA_ReadOnly)
			dem_mask = src.GetRasterBand(1).ReadAsArray()
		else:
			dem_mask = [[]]

		#????????????????????????++++++++++++++++++
		if(L_dem_layer != ""):
			#Terrain??????
			L_out, L_uri  = self.terainCalc(L_output_size, L_dem_mesh, L_dem_layer, L_geo_layer, mask_layer, dem_mask, "baseTerrain_DTM")
			arr11 = L_out[:int(L_dem_px/3+1), :int(L_dem_px/3+1)]
			arr12 = L_out[:int(L_dem_px/3+1), int(L_dem_px/3):int(L_dem_px*2/3+1)]
			arr13 = L_out[:int(L_dem_px/3+1), int(L_dem_px*2/3):]
			arr21 = L_out[int(L_dem_px/3):int(L_dem_px*2/3+1), :int(L_dem_px/3+1)]
			arr22 = L_out[int(L_dem_px/3):int(L_dem_px*2/3+1), int(L_dem_px/3):int(L_dem_px*2/3+1)]
			arr23 = L_out[int(L_dem_px/3):int(L_dem_px*2/3+1), int(L_dem_px*2/3):]
			arr31 = L_out[int(L_dem_px*2/3):, :int(L_dem_px/3+1)]
			arr32 = L_out[int(L_dem_px*2/3):, int(L_dem_px/3):int(L_dem_px*2/3+1)]
			arr33 = L_out[int(L_dem_px*2/3):, int(L_dem_px*2/3):]
			#raw??????(?????????????????????????????????"<" ????????????16?????????"u2") https://note.nkmk.me/python-numpy-dtype-astype/
			arr11.astype('<u2').tofile(self.output_path+"terrain11.raw")
			arr12.astype('<u2').tofile(self.output_path+"terrain12.raw")
			arr13.astype('<u2').tofile(self.output_path+"terrain13.raw")
			arr21.astype('<u2').tofile(self.output_path+"terrain21.raw")
			arr22.astype('<u2').tofile(self.output_path+"terrain22.raw")
			arr23.astype('<u2').tofile(self.output_path+"terrain23.raw")
			arr31.astype('<u2').tofile(self.output_path+"terrain31.raw")
			arr32.astype('<u2').tofile(self.output_path+"terrain32.raw")
			arr33.astype('<u2').tofile(self.output_path+"terrain33.raw")
			
			if(L_tex_layer !=""):
				#Texture??????
				self.textureCalc(L_output_size, L_tex_mesh, L_tex_layer, "baseTerrain_TEX")
				texlayer = QgsProject.instance().mapLayersByName("baseTerrain_TEX")[0]
				options = QgsMapSettings()
				options.setLayers([texlayer])
				options.setBackgroundColor(QColor(0, 0, 0))
				options.setOutputSize(QSize(L_dem_px/3, L_dem_px/3))
				options.setExtent(QgsRectangle(-L_output_size/2, L_output_size/2, -L_output_size/6, L_output_size/6))
				self.saveimg(options, self.output_path+"terrain11.jpg")
				options.setExtent(QgsRectangle(-L_output_size/6, L_output_size/2, L_output_size/6, L_output_size/6))
				self.saveimg(options, self.output_path+"terrain12.jpg")
				options.setExtent(QgsRectangle(L_output_size/6, L_output_size/2, L_output_size/2, L_output_size/6))
				self.saveimg(options, self.output_path+"terrain13.jpg")
				options.setExtent(QgsRectangle(-L_output_size/2, L_output_size/6, -L_output_size/6, -L_output_size/6))
				self.saveimg(options, self.output_path+"terrain21.jpg")
				options.setExtent(QgsRectangle(-L_output_size/6, L_output_size/6, L_output_size/6, -L_output_size/6))
				self.saveimg(options, self.output_path+"terrain22.jpg")
				options.setExtent(QgsRectangle(L_output_size/6, L_output_size/6, L_output_size/2, -L_output_size/6))
				self.saveimg(options, self.output_path+"terrain23.jpg")
				options.setExtent(QgsRectangle(-L_output_size/2, -L_output_size/6, -L_output_size/6, -L_output_size/2))
				self.saveimg(options, self.output_path+"terrain31.jpg")
				options.setExtent(QgsRectangle(-L_output_size/6, -L_output_size/6, L_output_size/6, -L_output_size/2))
				self.saveimg(options, self.output_path+"terrain32.jpg")
				options.setExtent(QgsRectangle(L_output_size/6, -L_output_size/6, L_output_size/2, -L_output_size/2))
				self.saveimg(options, self.output_path+"terrain33.jpg")
		
		#????????????????????????areTex>areaDTM>baseTEX>baseDTM????????????++++++++++++++++++
		layertree = QgsProject.instance().layerTreeRoot()
		try:
			layer = QgsProject.instance().mapLayersByName("baseTerrain_DTM")[0]
		except IndexError:
			pass
		else:
			lt = layertree.findLayer(layer.id())
			lt_clone = lt.clone()
			layertree.insertChildNode(0, lt_clone)
			layertree.removeChildNode(lt)

		layertree = QgsProject.instance().layerTreeRoot()
		try:
			layer = QgsProject.instance().mapLayersByName("areaTerrain_TEX")[0]
		except IndexError:
			pass
		else:
			lt = layertree.findLayer(layer.id())
			lt_clone = lt.clone()
			layertree.insertChildNode(0, lt_clone)
			layertree.removeChildNode(lt)

		layertree = QgsProject.instance().layerTreeRoot()
		try:
			layer = QgsProject.instance().mapLayersByName("areaTerrain_DTM")[0]
		except IndexError:
			pass
		else:
			lt = layertree.findLayer(layer.id())
			lt_clone = lt.clone()
			layertree.insertChildNode(0, lt_clone)
			layertree.removeChildNode(lt)

		#????????????============================
		elapsed_time = int(time.time() - start)
		elapsed_hour = elapsed_time // 3600
		elapsed_minute = (elapsed_time % 3600) // 60
		elapsed_second = (elapsed_time % 3600 % 60)
		print("????????????="+str(elapsed_hour).zfill(2) + ":" + str(elapsed_minute).zfill(2) + ":" + str(elapsed_second).zfill(2))
		
