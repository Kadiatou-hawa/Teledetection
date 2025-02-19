{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "fc1dfa0e-e438-4b4c-b60b-550e4b062ceb",
   "metadata": {},
   "outputs": [],
   "source": [
    "import rasterio\n",
    "import geopandas as gpd\n",
    "from rasterio.warp import calculate_default_transform, reproject, Resampling\n",
    "import numpy as np\n",
    "import os\n",
    "\n",
    "def appliquer_mask(input_image, mask_image, output_image):\n",
    "    with rasterio.open(input_image) as src:\n",
    "        image_data = src.read()\n",
    "        nodata_value = src.nodata\n",
    "\n",
    "    with rasterio.open(mask_image) as mask:\n",
    "        mask_data = mask.read(1)\n",
    "    \n",
    "    # Appliquer le masque (valeurs 0 pour non forêt)\n",
    "    image_data[:, mask_data == 0] = nodata_value\n",
    "\n",
    "    # Sauvegarder l'image masquée\n",
    "    with rasterio.open(output_image, 'w', driver='GTiff', count=image_data.shape[0], dtype=image_data.dtype,\n",
    "                       width=image_data.shape[2], height=image_data.shape[1], crs=src.crs, transform=src.transform,\n",
    "                       nodata=nodata_value) as dst:\n",
    "        dst.write(image_data)\n",
    "    \n",
    "    print(f\"L'image masquée a été sauvegardée sous {output_image}\")\n",
    "\n",
    "def pre_traiter_series(input_folder, output_path, shapefile_path, mask_path, resolution=10):\n",
    "    # Charger le shapefile pour l'emprise\n",
    "    shapefile = gpd.read_file(shapefile_path)\n",
    "    \n",
    "    # Récupérer les fichiers d'images\n",
    "    images = [f for f in os.listdir(input_folder) if f.endswith(\".tif\")]\n",
    "    \n",
    "    all_bands = []\n",
    "    \n",
    "    for image in images:\n",
    "        image_path = os.path.join(input_folder, image)\n",
    "        \n",
    "        with rasterio.open(image_path) as src:\n",
    "            # Rééchantillonnage à la résolution de 10m\n",
    "            transform, width, height = calculate_default_transform(src.crs, src.crs, src.width, src.height, *src.bounds, resolution=resolution)\n",
    "            profile = src.profile\n",
    "            profile.update(transform=transform, width=width, height=height, crs=src.crs, dtype=rasterio.uint16, nodata=0)\n",
    "\n",
    "            # Reprojection de l'image\n",
    "            output_temp_path = os.path.join(output_path, f\"temp_{image}\")\n",
    "            with rasterio.open(output_temp_path, 'w', **profile) as dst:\n",
    "                reproject(source=rasterio.band(src, 1), destination=rasterio.band(dst, 1), \n",
    "                          src_transform=src.transform, src_crs=src.crs, dst_transform=transform, dst_crs=src.crs,\n",
    "                          resampling=Resampling.nearest)\n",
    "            \n",
    "            all_bands.append(output_temp_path)\n",
    "    \n",
    "    # Fusionner toutes les bandes\n",
    "    with rasterio.open(all_bands[0]) as src:\n",
    "        data_stack = np.zeros((len(all_bands), src.height, src.width), dtype=np.uint16)\n",
    "\n",
    "    for i, band in enumerate(all_bands):\n",
    "        with rasterio.open(band) as src:\n",
    "            data_stack[i, :, :] = src.read(1)\n",
    "    \n",
    "    # Appliquer le masque de la forêt\n",
    "    appliquer_mask(data_stack, mask_path, \"results/data/img_pretaitees/Serie_temp_S2_allbands.tif\")\n",
    "    \n",
    "    print(\"Pré-traitement terminé, images sauvegardées dans 'results/data/img_pretaitees'.\")\n",
    "\n",
    "# Exemple d'appel\n",
    "input_folder = \"input_images\"  # dossier contenant les images\n",
    "output_path = \"results/data/img_pretaitees\"\n",
    "shapefile_path = \"emprise_etude.shp\"\n",
    "mask_path = \"masque_foret.tif\"\n",
    "pre_traiter_series(input_folder, output_path, shapefile_path, mask_path)\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "8182ca4f-0ee4-41d7-94fe-f3c680aead75",
   "metadata": {},
   "outputs": [],
   "source": [
    "import rasterio\n",
    "import geopandas as gpd\n",
    "from rasterio.warp import calculate_default_transform, reproject, Resampling\n",
    "import os\n",
    "\n",
    "def clip_image_to_extent(image_path, shapefile_path, output_path):\n",
    "    \"\"\"\n",
    "    Découpe une image raster selon l'emprise définie par un shapefile.\n",
    "    \"\"\"\n",
    "    with rasterio.open(image_path) as src:\n",
    "        # Charger l'emprise\n",
    "        shapefile = gpd.read_file(shapefile_path)\n",
    "        # Transformer l'emprise au système de coordonnées de l'image\n",
    "        shapefile = shapefile.to_crs(src.crs)\n",
    "        # Créer un masque à partir de l'emprise\n",
    "        mask = rasterio.features.geometry_mask(shapefile.geometry, transform=src.transform, invert=True, out_shape=src.shape)\n",
    "        # Appliquer le masque\n",
    "        image_data = src.read(1)\n",
    "        image_data[mask] = src.nodata\n",
    "\n",
    "        # Sauvegarder l'image découpée\n",
    "        with rasterio.open(output_path, 'w', driver='GTiff', count=1, dtype=image_data.dtype,\n",
    "                           width=image_data.shape[1], height=image_data.shape[0], crs=src.crs, transform=src.transform,\n",
    "                           nodata=src.nodata) as dst:\n",
    "            dst.write(image_data, 1)\n",
    "    print(f\"Image découpée sauvegardée sous {output_path}\")\n",
    "\n",
    "def resample_image(input_image, output_image, target_resolution=10):\n",
    "    \"\"\"\n",
    "    Rééchantillonne une image raster à une résolution cible.\n",
    "    \"\"\"\n",
    "    with rasterio.open(input_image) as src:\n",
    "        # Calculer la transformation et les nouvelles dimensions\n",
    "        transform, width, height = calculate_default_transform(\n",
    "            src.crs, src.crs, src.width, src.height, *src.bounds, resolution=target_resolution)\n",
    "        profile = src.profile\n",
    "        profile.update(transform=transform, width=width, height=height, dtype=rasterio.float32)\n",
    "\n",
    "        # Rééchantillonnage\n",
    "        with rasterio.open(output_image, 'w', **profile) as dst:\n",
    "            for i in range(1, src.count + 1):\n",
    "                reproject(\n",
    "                    source=rasterio.band(src, i),\n",
    "                    destination=rasterio.band(dst, i),\n",
    "                    src_transform=src.transform,\n",
    "                    src_crs=src.crs,\n",
    "                    dst_transform=transform,\n",
    "                    dst_crs=src.crs,\n",
    "                    resampling=Resampling.nearest)\n",
    "    print(f\"Image rééchantillonnée sauvegardée sous {output_image}\")\n",
    "\n",
    "def merge_bands_to_multispectral(input_bands, output_image):\n",
    "    \"\"\"\n",
    "    Fusionne plusieurs bandes raster en une seule image multi-spectrale.\n",
    "    \"\"\"\n",
    "    with rasterio.open(input_bands[0]) as src:\n",
    "        profile = src.profile\n",
    "        profile.update(count=len(input_bands))\n",
    "\n",
    "        with rasterio.open(output_image, 'w', **profile) as dst:\n",
    "            for i, band_path in enumerate(input_bands, start=1):\n",
    "                with rasterio.open(band_path) as band:\n",
    "                    dst.write(band.read(1), i)\n",
    "    print(f\"Image multi-spectrale sauvegardée sous {output_image}\")\n",
    "\n",
    "def apply_forest_mask(image_path, mask_path, output_image):\n",
    "    \"\"\"\n",
    "    Applique un masque de forêt à une image raster.\n",
    "    \"\"\"\n",
    "    with rasterio.open(image_path) as src:\n",
    "        # Charger le masque de forêt\n",
    "        forest_mask = rasterio.open(mask_path).read(1)\n",
    "\n",
    "        # Appliquer le masque à l'image\n",
    "        image_data = src.read(1)\n",
    "        image_data[forest_mask == 0] = src.nodata  # Masquer les zones non forestières\n",
    "\n",
    "        # Sauvegarder l'image après application du masque\n",
    "        with rasterio.open(output_image, 'w', driver='GTiff', count=1, dtype=image_data.dtype,\n",
    "                           width=image_data.shape[1], height=image_data.shape[0], crs=src.crs, transform=src.transform,\n",
    "                           nodata=src.nodata) as dst:\n",
    "            dst.write(image_data, 1)\n",
    "    print(f\"Image avec masque de forêt sauvegardée sous {output_image}\")\n",
    "\n",
    "def pre_process_image(image_path, shapefile_path, forest_mask_path, output_dir):\n",
    "    \"\"\"\n",
    "    Fonction principale de pré-traitement des images Sentinel-2.\n",
    "    \"\"\"\n",
    "    # 1. Découper l'image selon l'emprise\n",
    "    clipped_image_path = os.path.join(output_dir, \"clipped_image.tif\")\n",
    "    clip_image_to_extent(image_path, shapefile_path, clipped_image_path)\n",
    "\n",
    "    # 2. Rééchantillonner l'image à une résolution de 10 mètres\n",
    "    resampled_image_path = os.path.join(output_dir, \"resampled_image.tif\")\n",
    "    resample_image(clipped_image_path, resampled_image_path, target_resolution=10)\n",
    "\n",
    "    # 3. Fusionner les bandes pour créer une image multi-spectrale\n",
    "    input_bands = [resampled_image_path]  # Remplacez par les chemins des différentes bandes à fusionner\n",
    "    multispectral_image_path = os.path.join(output_dir, \"multispectral_image.tif\")\n",
    "    merge_bands_to_multispectral(input_bands, multispectral_image_path)\n",
    "\n",
    "    # 4. Appliquer le masque de forêt\n",
    "    final_image_path = os.path.join(output_dir, \"final_image_with_forest_mask.tif\")\n",
    "    apply_forest_mask(multispectral_image_path, forest_mask_path, final_image_path)\n",
    "\n",
    "    print(f\"Pré-traitement terminé. Image finale sauvegardée sous {final_image_path}\")\n",
    "\n",
    "# Exemple d'utilisation\n",
    "image_path = 'path_to_your_image.tif'\n",
    "shapefile_path = 'path_to_your_shapefile.shp'\n",
    "forest_mask_path = 'path_to_forest_mask.tif'\n",
    "output_dir = 'path_to_output_directory'\n",
    "\n",
    "pre_process_image(image_path, shapefile_path, forest_mask_path, output_dir)\n"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.12.6"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
