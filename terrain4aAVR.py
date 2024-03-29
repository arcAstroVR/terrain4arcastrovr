# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Terrain4aAVR
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
from .terrain4aAVR_dialog import Terrain4aAVRDialog
import os, sys, time, datetime
import processing
import numpy as np
from osgeo import gdal


class Terrain4aAVR:
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
			'Terrain4aAVR_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)
			QCoreApplication.installTranslator(self.translator)

		# Declare instance attributes
		self.actions = []
		self.menu = self.tr(u'&Terrain for arcAstroVR')

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
		return QCoreApplication.translate('Terrain4aAVR', message)


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

		icon_path = ':/plugins/terrain4aAVR/icon.png'
		self.add_action(
			icon_path,
			text=self.tr(u'Terrain4aAVR'),
			callback=self.run,
			parent=self.iface.mainWindow())

		# will be set False in run()
		self.first_start = True


	def unload(self):
		"""Removes the plugin menu item and icon from QGIS GUI."""
		#self.marker.hide()
		#self.wideline.hide()
		#self.narrowline.hide()
		#self.canvas.scene().removeItem(self.marker)
		#self.canvas.scene().removeItem(self.wideline)
		#self.canvas.scene().removeItem(self.narrowline)
		#self.canvas.refreshAllLayers()

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
			self.dlg = Terrain4aAVRDialog()

		#出力諸元（output_size：出力幅(m)、dem_mesh：Terrainの解像度(m)、tex_mesh：Textureの解像度（m））
		#Unity用のTerrainサイズ(dem_px)は32,64,128,256,1024,2048,4096pxのいずれかである必要があるので注意。
		#入力データのメッシュ解像度(dem_px)が出力データのメッシュ解像度(output_size)より細かいとブロックが出やすいので注意。一致させるのが理想。
		self.L_output_size = 300000
		self.L_dem_px = 4096*3		#軽量の確認処理の際には256*3程度が適当。通常時は4096*3
		self.L_dem_mesh = self.L_output_size/self.L_dem_px
		self.L_tex_mesh = self.L_dem_mesh
		self.S_dem_px = 4096		#軽量の確認処理の際には256程度が適当。通常時は4096
		self.S_dem_mesh = self.dlg.doubleSpinBox.value()
		self.S_output_size = self.S_dem_px * self.S_dem_mesh
		self.S_tex_mesh = self.S_dem_mesh/5
		print("mesh="+str(self.S_dem_mesh)+", narrow area="+str(self.S_output_size))

		#UnityTerrain用の調整値（zoffset：標高オフセット、h_max：最大値を何mにするか、down：マスクエリアのベース地形を何m下降させるか）
		#h_max = 10000、zoffset=1000にした時、以下のような関係になる
		#標高-1000m：GeoTiff=0、Unity Box=0
		#標高0m：GeoTiif=6553.6、Unity Box=1000
		#標高9000m：GeoTiff=65536、Unity Box=10000
		self.zoffset = 1000
		self.h_max = 10000
		self.down = 3

		#定数定義
		eqEarth=1.156							#等価地球半径（倍）
		self.A = 6378137.0*eqEarth					# a(地球楕円体長半径(赤道面平均半径))
		ONE_F = 298.257223563					# 1 / f(地球楕円体扁平率=(a - b) / a)
		self.B = self.A * (1.0 - 1.0 / ONE_F)					# b(地球楕円体短半径)
		self.E2 = (1.0 / ONE_F) * (2 - (1.0 / ONE_F))		# e^2 = 2 * f - f * f = (a^2 - b^2) / a^2
		self.ED2    = self.E2 * self.A * self.A / (self.B * self.B)					# e'^2= (a^2 - b^2) / b^2

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
			elif (layer.type() == QgsMapLayer.RasterLayer) and (layer.name() !="narrowTerrain_DTM") and (layer.name() !="narrowTerrain_TEX") and (layer.name() !="wideTerrain_DTM") and (layer.name() !="wideTerrain_TEX"):
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

		#メインCanvasを取得
		self.canvas = iface.mapCanvas()

		#マーカー描画設定
		self.marker = QgsVertexMarker(self.canvas)
		self.marker.setColor(QColor(255,0, 0))
		self.marker.setIconSize(20)
		self.marker.setIconType(QgsVertexMarker.ICON_X)
		self.marker.setPenWidth(1)
		
		#ライン描画設定
		self.wideline = QgsRubberBand(self.canvas, True)
		self.wideline.setColor(QColor(255, 0, 0))
		self.wideline.setWidth(2)
		self.narrowline = QgsRubberBand(self.canvas, True)
		self.narrowline.setColor(QColor(0, 255, 0))
		self.narrowline.setWidth(2)

		# lineEdit（緯度経度）のチェンジイベント
		#self.dlg.lineEdit1_1.editingFinished.connect(self.lineEdit1Activated) 
		self.dlg.lineEdit1_1.textEdited.connect(self.lineEdit1Activated) 
		
		# comboBoxのチェンジイベント
		self.dlg.comboBox2_1.currentIndexChanged.connect(self.combobox2Activated) 
		self.dlg.comboBox3_1.currentIndexChanged.connect(self.combobox3Activated) 

		# PREPARE SAVE Dir
		self.dlg.mQgsFileWidget_outputPath.setFilePath(os.path.expanduser('~/Desktop'))
		self.dlg.mQgsFileWidget_outputPath.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
		self.dlg.mQgsFileWidget_outputPath.setDialogTitle("Select a save directory")

		# doubleSpinBoxのチェンジイベント
		self.dlg.doubleSpinBox.valueChanged.connect(self.spinboxActivated) 

		# show the dialog
		self.dlg.show()

		# メインcanvasのCRSをlat,lon中心の正射投影に変更
		self.lineEdit1Activated()

		# Run the dialog event loop
		result = self.dlg.exec_()
		# See if OK was pressed
		if result:
			# Do something useful here - delete the line containing pass and
			# substitute with your code.
			self.main()
			pass


	#ダイアログチェンジイベント
	def lineEdit1Activated(self):
		center_str = self.dlg.lineEdit1_1.text().split(",")
		if len(center_str) == 2:
			if self.isfloat(center_str[0]) and self.isfloat(center_str[1]):
				self.lat = float(center_str[0])		#緯度
				self.lon = float(center_str[1])	#経度
			else:
				#QMessageBox.information(None, 'Error', u'Invalid latitude/longitude values : Err code1')
				return
		else: #MapCanvas中心の緯度・経度取得
			if (center_str[0] != "") or len(center_str) > 2:
				#QMessageBox.information(None, 'Error', u'Invalid latitude/longitude values : Err code2')
				return
			center = self.iface.mapCanvas().center()
			canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
			epsg4326_crs = QgsCoordinateReferenceSystem(4326)
			crs_trans = QgsCoordinateTransform(canvas_crs, epsg4326_crs, QgsProject.instance())
			pt4326 = crs_trans.transform(center)
			self.lat = float(pt4326.y())	#緯度
			self.lon = float(pt4326.x())	#経度
		if (self.lat < -90) or (self.lat > 90) or (self.lon < -180) or (self.lon >180):
			QMessageBox.information(None, 'Error', u'Invalid latitude/longitude values : Err code3')
		else:
			print("Center coordinates (latitude, longitude) ="+str(self.lat)+", "+str(self.lon))
		
		#指定座標を中心とした正斜投影のCRSをセット
		self.crs = QgsCoordinateReferenceSystem().fromProj4('+proj=ortho +lat_0='+str(self.lat)+' +lon_0='+str(self.lon)+' +x_0=0 +y_0=0 +ellps=sphere +units=m +no_defs')
		QgsProject.instance().setCrs(self.crs)
		
		#指定座標にキャンバスを移動
		rect = QgsRectangle( QgsPointXY(-200000, -200000), QgsPointXY(+200000, +200000))
		self.iface.mapCanvas().setExtent(rect)
		self.iface.mapCanvas().refresh()
		
		#中心マーカー描画
		self.marker.setCenter(QgsPointXY(0,0))
		
		#広域境界描画
		points =[QgsPoint(-150000, -150000), QgsPoint(-150000, 150000), QgsPoint(150000, 150000),QgsPoint(150000, -150000),QgsPoint(-150000, -150000)]
		self.wideline.setToGeometry(QgsGeometry.fromPolyline(points), None)
		
		#キャンバス再描画
		self.canvas.refreshAllLayers()

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
			self.narrowline.show()
			self.spinboxActivated()
		else:
			self.dlg.label3_2.setEnabled(False)
			self.dlg.label3_3.setEnabled(False)
			self.dlg.label3_4.setEnabled(False)
			self.dlg.label3_5.setEnabled(False)
			self.dlg.comboBox3_2.setEnabled(False)
			self.dlg.comboBox3_3.setEnabled(False)
			self.dlg.doubleSpinBox.setEnabled(False)
			self.narrowline.hide()

	def spinboxActivated(self):
		area = self.dlg.doubleSpinBox.value() * self.S_dem_px
		self.dlg.label3_5.setText("（narrow area : "+ str('{:.1f}'.format(area)) +"m）")
		#狭域境界描画
		points =[QgsPoint(-area/2, -area/2), QgsPoint(-area/2, area/2), QgsPoint(area/2, area/2),QgsPoint(area/2, -area/2),QgsPoint(-area/2, -area/2)]
		self.narrowline.setToGeometry(QgsGeometry.fromPolyline(points), None)

	#小数点変換可能確認
	def isfloat(self, parameter):
		if not parameter.isdecimal():
			try:
				float(parameter)
				return True
			except ValueError:
				return False
		else:
			return True

	#BLH (lat, lon, ht) -> ECEF 変換(x, y, z)
	def blh2ecef(self, lat, lon, ht):
		lat_rad = np.deg2rad(lat)
		lon_rad = np.deg2rad(lon)
		n = lambda x: self.A / np.sqrt(1.0 - self.E2 * np.sin(np.deg2rad(x))**2)
		x = (n(lat) + ht) * np.cos(lat_rad) * np.cos(lon_rad)
		y = (n(lat) + ht) * np.cos(lat_rad) * np.sin(lon_rad)
		z = (n(lat) * (1.0 - self.E2) + ht) * np.sin(lat_rad)
		return [x, y, z]
	
	#ECEF 変換(x, y, z) -> BLH (lat, lon, ht) 
	def ecef2blh(self, x, y, z):
		n = lambda x: self.A / np.sqrt(1.0 - self.E2 * np.sin(np.deg2rad(x))**2)
		p = np.sqrt(x * x + y * y)
		theta = np.arctan2(z * self.A, p * self.B)
		lat = np.rad2deg(np.arctan2( z + self.ED2 * self.B * np.sin(theta)**3, p - self.E2 * self.A * np.cos(theta)**3))
		lon = np.rad2deg(np.arctan2(y, x))
		ht = (p / np.cos(np.deg2rad(lat))) - n(lat)
		return [lat, lon, ht]
	
	# y 軸を軸とした回転行列
	def mat_y(self, ang):
		a = np.deg2rad(ang)
		c = np.cos(a)
		s = np.sin(a)
		return np.array([[c, 0.0, -s],[ 0.0, 1.0, 0.0],[ s, 0.0, c]])
	
	# z 軸を軸とした回転行列
	def mat_z(self, ang):
		a = np.deg2rad(ang)
		c = np.cos(a)
		s = np.sin(a)
		return np.array([[ c, s, 0.0],[ -s, c, 0.0],[0.0, 0.0, 1.0]])
	
	# jpg出力
	def saveimg(self, options, path):
		render = QgsMapRendererParallelJob(options)
		render.start()
		render.waitForFinished()
		img = render.renderedImage()
		img.save(path, "jpg")
	
	def terainCalc(self, width, dem_mesh, dem_layer, geo_layer, mask_layer, mask_array, out_name):
		#出力領域(m)：unity用Terrain対応の為に計算領域に+1pxの範囲を指定している
		area_rect = '-'+str(width/2)+','+str(width/2+dem_mesh)+',-'+str(width/2+dem_mesh)+','+str(width/2)

		layer = QgsProject.instance().mapLayersByName(dem_layer)[0]
		uri = layer.dataProvider().dataSourceUri()

		#DTM：正斜投影で再投影し画像範囲でクリップ
		if(out_name == "narrowTerrain_DTM")and(mask_layer !=""):		#詳細地形処理で且つマスク指定ありの場合
			#DTM：詳細地形をメモリ上にラスタ展開、
			parameter = { 'BANDS' : [1], 'DATA_TYPE' : 7, 'INPUT' : uri, 'OPTIONS' : '', 'OUTPUT' : 'TEMPORARY_OUTPUT' }
			memory_uri =  processing.run('gdal:rearrange_bands', parameter)
			#self.iface.addRasterLayer(memory_uri ['OUTPUT'], 'rearrangeDEM')
	
			#Mask_Layerの領域下降処理
			layer = QgsProject.instance().mapLayersByName(mask_layer)[0]
			parameter = { 'ADD' : True, 'BURN' : -self.down, 'EXTRA' : '', 'INPUT' : layer, 'INPUT_RASTER' : memory_uri['OUTPUT'], 'OUTPUT' : 'TEMPORARY_OUTPUT' }
			memory_uri = processing.run('gdal:rasterize_over_fixed_value', parameter)
			#self.iface.addRasterLayer(memory_uri ['OUTPUT'], 'over_fixedDEM')
			
			parameter ={'DATA_TYPE' : 7, 'INPUT' : memory_uri['OUTPUT'], 'OUTPUT' : 'TEMPORARY_OUTPUT', 'TARGET_CRS' : self.crs, 'TARGET_RESOLUTION' : dem_mesh ,'TARGET_EXTENT' : area_rect, 'TARGET_EXTENT_CRS' : self.crs }
		else:			#ベース地形処理、またはマスク指定がない詳細地形処理
			parameter ={'DATA_TYPE' : 7, 'INPUT' : uri, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'TARGET_CRS' : self.crs, 'TARGET_RESOLUTION' : dem_mesh ,'TARGET_EXTENT' : area_rect, 'TARGET_EXTENT_CRS' : self.crs }
		dem = processing.run('gdal:warpreproject', parameter)
		#self.iface.addRasterLayer(dem['OUTPUT'], 'orthoDEM')

		#DTM：numpy配列読み込み
		src = gdal.Open(dem['OUTPUT'], gdal.GA_ReadOnly)
		dem_array = src.GetRasterBand(1).ReadAsArray()

		if(geo_layer != ""):		#ジオイド指定がある場合
			#GEOID：正斜投影で再投影し画像範囲でクリップ
			layer = QgsProject.instance().mapLayersByName(geo_layer)[0]
			uri = layer.dataProvider().dataSourceUri()
			parameter ={'DATA_TYPE' : 7, 'INPUT' : uri, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'TARGET_CRS' : self.crs, 'TARGET_RESOLUTION' : dem_mesh ,'TARGET_EXTENT' : area_rect, 'TARGET_EXTENT_CRS' : self.crs }
			geo = processing.run('gdal:warpreproject', parameter)
			#self.iface.addRasterLayer(geo['OUTPUT'], 'orthoGEO')

			#GEOID：numpy配列読み込み
			src = gdal.Open(geo['OUTPUT'], gdal.GA_ReadOnly)
			geo_array = src.GetRasterBand(1).ReadAsArray()
			geo_array[geo_array < 0] = 0

			#DTM/GEOID配列の統合
			out_array = dem_array + geo_array
		else:						#ジオイド指定がない場合
			print(out_name+" does not set GEOID")
			out_array = dem_array
	
		#プログレスバーの表示
		progressMessageBar = iface.messageBar().createMessage("Calculate DTM: "+dem_layer)
		self.progress = QProgressBar()
		self.progress.setMaximum(100)
		self.progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
		progressMessageBar.layout().addWidget(self.progress)
		self.iface.messageBar().pushWidget(progressMessageBar, Qgis.Info)

		#球体補正値を加算
		half_width = width/2
		px_size = width/dem_mesh
		plus_px_size = int(px_size +1)
		half_px_size = px_size / 2
		co_prog = 100/plus_px_size
		co_level = 65536/self.h_max
		mask = False
		if type(mask_array).__module__ == "numpy": 		#詳細地形マスクの指定がある場合
			mask = True
			mask_w = int(mask_array.shape[0]/2)
		for h in range(0, plus_px_size):
			QApplication.processEvents()
			self.progress.setValue(h*co_prog+1)
			for w in range(0, plus_px_size):
				z = out_array[w,h]	#標高値
				ecef_t = np.dot(self.mat, [w*dem_mesh - half_width, h*dem_mesh - half_width, 0])
				ecef = np.add(self.ecef_o, ecef_t)
				blh = self.ecef2blh(*ecef)
				#blh[]=[lat, lon, ht]：blh[2]=球体降下値（+値）
				#zoffset：標高オフセット、down：マスクエリアの降下量
				level = (z-blh[2]+self.zoffset)*co_level	#0〜65536(-1000m=0, 0m=6553, 9000m=65536)：球体補正後の高さ
				#詳細マスク付き基本地形
				if out_name == "wideTerrain_DTM" and mask:
					center_x = int(w - half_px_size)
					center_y = int(h - half_px_size)
					if abs(center_x) < mask_w and abs(center_y) < mask_w:	#マスク領域内の処理
						mask_z = mask_array[int(center_x+mask_w),int(center_y+mask_w)]	#0〜65536(-1000m=0, 0m=6553, 9000m=65536)：球体補正後の高さ
						if mask_z > (self.zoffset-blh[2])*co_level :	#詳細地形が地球楕円体より高い場合は、詳細地形-self.downを基本地形にセットする。
							level = mask_z - self.down*co_level
				#詳細マスクなし基本地形 / 詳細地形：標高データが水面より下の場合、地球楕円体-1mを設定
				elif dem_array[w,h] <= 0:
					level = (self.zoffset-blh[2]-1)*co_level
				#全ての地形
				if dem_array[w,h] == np.nan or level < 0: #nodataまたは球体補正後の高さが負の場合は0を設定
					level = 0
				out_array[w,h] = level

		#プログレスバーの非表示
		self.iface.messageBar().clearWidgets()

		#geotiff書き出し
		geotransform = src.GetGeoTransform()
		originY = geotransform[3]
		originX = geotransform[0]
		dst = self.output_path + out_name+".tif"
		dtype = gdal.GDT_UInt16	# others: gdal.GDT_Byte, ...
		band = 1					# バンド数
		dst_raster = gdal.GetDriverByName('GTiff').Create(dst, int(px_size+1), int(px_size+1), band, dtype)
		dst_raster.SetGeoTransform((originX, dem_mesh, 0, originY, 0, -dem_mesh))
		dst_band = dst_raster.GetRasterBand(1)
		dst_band.WriteArray(out_array)
		dst_band.FlushCache()
		dst_raster = None
		
		#レイヤー追加
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
		#出力領域(m)
		area_rect = '-'+str(width/2)+','+str(width/2)+',-'+str(width/2)+','+str(width/2)
	
		#TEXTURE：Canvasの投影形式でxyzタイルを画像範囲でクリップ
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
		# レイヤーの初期設定
		L_dem_layer = ""
		L_geo_layer = ""
		L_tex_layer = ""
		S_dem_layer = ""
		S_geo_layer = ""
		S_tex_layer = ""
		mask_layer = ""
		
		self.output_path = self.dlg.mQgsFileWidget_outputPath.filePath()+"/"
		if self.output_path == "/":
			QMessageBox.information(None, 'Error', u'Destination not specified : Err code4')
			return
		else:
			print("Save to ="+self.output_path)
		
		#入力レイヤー（L_はベース地形用、S_は詳細地形用）
		L_dem_layer = self.single_list[self.dlg.comboBox2_1.currentIndex()]
		L_geo_layer = self.single_list[self.dlg.comboBox2_2.currentIndex()]
		L_tex_layer = self.multi_list[self.dlg.comboBox2_3.currentIndex()]
		S_dem_layer = self.single_list[self.dlg.comboBox3_1.currentIndex()]
		S_geo_layer = self.single_list[self.dlg.comboBox3_2.currentIndex()]
		S_tex_layer = self.multi_list[self.dlg.comboBox3_3.currentIndex()]
		mask_layer = self.vector_list[self.dlg.comboBox4.currentIndex()]
		print("wideTerrain layer="+L_dem_layer+", "+L_geo_layer+", "+L_tex_layer)
		print("narrowTerrain layer="+S_dem_layer+", "+S_geo_layer+", "+S_tex_layer)
		print("Mask layer="+mask_layer)
		
		if (self.dlg.comboBox2_1.currentIndex() == 0)and(self.dlg.comboBox3_1.currentIndex() == 0):
			QMessageBox.information(None, 'Error', u'DEM layer not specified : Err code5')
			return
		
		#時間計測開始
		start = time.time()
		print("Start time="+str(datetime.datetime.now()))
		
		#ERN->ECEF変換行列の作製
		mat_0 = self.mat_z(-90.0)
		mat_1 = self.mat_y(self.lat-90.0)
		mat_2 = self.mat_z(-self.lon)
		self.mat = np.dot(np.dot(mat_2,mat_1),mat_0)
		
		#原点のECEFを取得
		self.ecef_o = self.blh2ecef(self.lat, self.lon, 0)

		#詳細地形の処理++++++++++++++++++
		if(S_dem_layer != ""):
			#Terrain作成
			S_out, S_uri = self.terainCalc(self.S_output_size, self.S_dem_mesh, S_dem_layer, S_geo_layer, mask_layer, 0, "narrowTerrain_DTM")
			#raw保存(リトルエンディアン形式"<" 符号なし16ビット"u2") https://note.nkmk.me/python-numpy-dtype-astype/
			S_out.astype('<u2').tofile(self.output_path+"terrain00.raw")
			
			if(S_tex_layer !=""):
				#Texture作成
				self.textureCalc(self.S_output_size, self.S_tex_mesh, S_tex_layer, "narrowTerrain_TEX")
				pxsize = self.S_output_size/self.S_tex_mesh
				if pxsize > 16384:
					pxsize = 16384
				texlayer = QgsProject.instance().mapLayersByName("narrowTerrain_TEX")[0]
				options = QgsMapSettings()
				options.setLayers([texlayer])
				options.setBackgroundColor(QColor(0, 0, 0))
				options.setOutputSize(QSize(pxsize, pxsize))
				options.setExtent(QgsRectangle(-self.S_output_size/2, self.S_output_size/2, self.S_output_size/2, -self.S_output_size/2))
				self.saveimg(options, self.output_path+"terrain00.jpg")
			
			#Terrain Mask用Array作成
			s_width = str(self.S_output_size/2)
			area_rect = '-'+s_width+','+s_width+',-'+s_width+','+s_width
			
			#正斜投影・近傍の最小値データ（ 'RESAMPLING' : 8）で再投影しベース地形解像度でクリップし直し
			uri = S_uri
			parameter ={'DATA_TYPE' : 7, 'INPUT' : uri, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'RESAMPLING' : 8, 'TARGET_CRS' : self.crs, 'TARGET_RESOLUTION' : self.L_dem_mesh ,'TARGET_EXTENT' : area_rect, 'TARGET_EXTENT_CRS' : self.crs }
			mask = processing.run('gdal:warpreproject', parameter)
			#iface.addRasterLayer(mask['OUTPUT'], 'areaTerrain_MASK')
			#areaTerrain_MASK：numpy配列読み込み
			src = gdal.Open(mask['OUTPUT'], gdal.GA_ReadOnly)
			dem_mask = src.GetRasterBand(1).ReadAsArray()
		else:
			dem_mask = [[]]

		#ベース地形の処理++++++++++++++++++
		if(L_dem_layer != ""):
			#Terrain作成
			L_out, L_uri  = self.terainCalc(self.L_output_size, self.L_dem_mesh, L_dem_layer, L_geo_layer, mask_layer, dem_mask, "wideTerrain_DTM")
			arr11 = L_out[:int(self.L_dem_px/3+1), :int(self.L_dem_px/3+1)]
			arr12 = L_out[:int(self.L_dem_px/3+1), int(self.L_dem_px/3):int(self.L_dem_px*2/3+1)]
			arr13 = L_out[:int(self.L_dem_px/3+1), int(self.L_dem_px*2/3):]
			arr21 = L_out[int(self.L_dem_px/3):int(self.L_dem_px*2/3+1), :int(self.L_dem_px/3+1)]
			arr22 = L_out[int(self.L_dem_px/3):int(self.L_dem_px*2/3+1), int(self.L_dem_px/3):int(self.L_dem_px*2/3+1)]
			arr23 = L_out[int(self.L_dem_px/3):int(self.L_dem_px*2/3+1), int(self.L_dem_px*2/3):]
			arr31 = L_out[int(self.L_dem_px*2/3):, :int(self.L_dem_px/3+1)]
			arr32 = L_out[int(self.L_dem_px*2/3):, int(self.L_dem_px/3):int(self.L_dem_px*2/3+1)]
			arr33 = L_out[int(self.L_dem_px*2/3):, int(self.L_dem_px*2/3):]
			#raw保存(リトルエンディアン形式"<" 符号なし16ビット"u2") https://note.nkmk.me/python-numpy-dtype-astype/
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
				#Texture作成
				self.textureCalc(self.L_output_size, self.L_tex_mesh, L_tex_layer, "wideTerrain_TEX")
				texlayer = QgsProject.instance().mapLayersByName("wideTerrain_TEX")[0]
				options = QgsMapSettings()
				options.setLayers([texlayer])
				options.setBackgroundColor(QColor(0, 0, 0))
				options.setOutputSize(QSize(self.L_dem_px/3, self.L_dem_px/3))
				options.setExtent(QgsRectangle(-self.L_output_size/2, self.L_output_size/2, -self.L_output_size/6, self.L_output_size/6))
				self.saveimg(options, self.output_path+"terrain11.jpg")
				options.setExtent(QgsRectangle(-self.L_output_size/6, self.L_output_size/2, self.L_output_size/6, self.L_output_size/6))
				self.saveimg(options, self.output_path+"terrain12.jpg")
				options.setExtent(QgsRectangle(self.L_output_size/6, self.L_output_size/2, self.L_output_size/2, self.L_output_size/6))
				self.saveimg(options, self.output_path+"terrain13.jpg")
				options.setExtent(QgsRectangle(-self.L_output_size/2, self.L_output_size/6, -self.L_output_size/6, -self.L_output_size/6))
				self.saveimg(options, self.output_path+"terrain21.jpg")
				options.setExtent(QgsRectangle(-self.L_output_size/6, self.L_output_size/6, self.L_output_size/6, -self.L_output_size/6))
				self.saveimg(options, self.output_path+"terrain22.jpg")
				options.setExtent(QgsRectangle(self.L_output_size/6, self.L_output_size/6, self.L_output_size/2, -self.L_output_size/6))
				self.saveimg(options, self.output_path+"terrain23.jpg")
				options.setExtent(QgsRectangle(-self.L_output_size/2, -self.L_output_size/6, -self.L_output_size/6, -self.L_output_size/2))
				self.saveimg(options, self.output_path+"terrain31.jpg")
				options.setExtent(QgsRectangle(-self.L_output_size/6, -self.L_output_size/6, self.L_output_size/6, -self.L_output_size/2))
				self.saveimg(options, self.output_path+"terrain32.jpg")
				options.setExtent(QgsRectangle(self.L_output_size/6, -self.L_output_size/6, self.L_output_size/2, -self.L_output_size/2))
				self.saveimg(options, self.output_path+"terrain33.jpg")
		
		#レイヤの表示順（areTex>areaDTM>baseTEX>baseDTM）を変更++++++++++++++++++
		layertree = QgsProject.instance().layerTreeRoot()
		try:
			layer = QgsProject.instance().mapLayersByName("wideTerrain_DTM")[0]
		except IndexError:
			pass
		else:
			lt = layertree.findLayer(layer.id())
			lt_clone = lt.clone()
			layertree.insertChildNode(0, lt_clone)
			layertree.removeChildNode(lt)

		layertree = QgsProject.instance().layerTreeRoot()
		try:
			layer = QgsProject.instance().mapLayersByName("narrowTerrain_TEX")[0]
		except IndexError:
			pass
		else:
			lt = layertree.findLayer(layer.id())
			lt_clone = lt.clone()
			layertree.insertChildNode(0, lt_clone)
			layertree.removeChildNode(lt)

		layertree = QgsProject.instance().layerTreeRoot()
		try:
			layer = QgsProject.instance().mapLayersByName("narrowTerrain_DTM")[0]
		except IndexError:
			pass
		else:
			lt = layertree.findLayer(layer.id())
			lt_clone = lt.clone()
			layertree.insertChildNode(0, lt_clone)
			layertree.removeChildNode(lt)

		#出力時間============================
		elapsed_time = int(time.time() - start)
		elapsed_hour = elapsed_time // 3600
		elapsed_minute = (elapsed_time % 3600) // 60
		elapsed_second = (elapsed_time % 3600 % 60)
		print("output time="+str(elapsed_hour).zfill(2) + ":" + str(elapsed_minute).zfill(2) + ":" + str(elapsed_second).zfill(2))
		
