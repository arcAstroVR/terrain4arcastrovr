# terrain4arcastrovr
This is a QGIS Plugin that creates terrain data for arcAstroVR.<br>arcAstroVR is a visualization software for archaeological remains and background celestial bodies. This plugin outputs elevation and texture data for a 300km square 24m mesh with orthophorization, sphere correction and optical correction.

## Installation Instructions & Quick Start
This Plugin requires QGIS.  
 * [QGIS app](https://qgis.org/)  
 * [terrain4arcastrovr](https://arcastrovr.org/download.html?id=plugin)  

Download and Setup  
 1. Download the latest version of [QGIS](https://qgis.org/) from [QGIS.org](https://qgis.org/). 
 2. Download the [terrain4arcastrovr.zip](https://arcastrovr.org/download.html?id=plugin) from [arcAstroVR.org](https://arcastrovr.org).
 4. Launch QGIS.  
 5. Select `Plugins > Manage and Install Plugins...` from the menu bar.
 6. Click the `Install from ZIP` in the left tab.
 7. Set the location of terrain4arcastrovr.zip in the ZIP file path field.
 8. Click `Install Plugin`.
 9. `terrain4arcastrovr` icon appears in the second row of the QGIS icon bar, second from the far right.

How to use terrain4arcastrovr  
 1. Register geotiff data and texture data for a 150 km radius area from the center point of the terrain you wish to create in a layer in QGIS.
 2. Click `terrain4arcastrovr` icon.
 3. Set the latitude and longitude of the center location in the `Input field`.  
 4. Set the terrain elevation data layer to the `basic terrain DEM layer`.  
 5. If you have it, set the Geoid elevation data layer to the `basic terrain Geoid layer`.
 6. If you have it, set the Texture data layer to the `basic terrain Texture layer`.
 7. If you have terrain data more detailed than a 10-meter mesh, you can add detailed terrain data.<br>In this case, set the corresponding Layers to the `detailed terrain DEM layer`, the `detailed terrain Geoid layer`, and the `detailed terrain Texture layer`, respectively.<br>In the Mesh field, enter the resolution of the detailed terrain.
 8. Set the save path.
 9. Click `OK` button.
 10. Put the created data into the terrain directory of the dataset for arcAstroVR.


## License
Released April 1, 2022 under GPLv3.
