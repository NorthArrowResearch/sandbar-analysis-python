"""
Merges a folder of campsite polyline ShapeFiles into a single polygon ShapeFile
It assumes each ShapeFile is named like this: <site_name>_<survey_date>_<other_stuff>.shp
Philip Bailey
8 Jan 2024
"""
import os
import re
import argparse
from osgeo import ogr


def convert_polyline_to_polygon(input_shapefile, output_shapefile):
    """
    Merge the input ShapeFile into the output ShapeFile
    """
    # Open the input shapefile
    input_ds = ogr.Open(input_shapefile)
    if input_ds is None:
        raise ValueError(f'Could not open input shapefile {input_shapefile}')
    input_layer = input_ds.GetLayerByIndex(0)
    input_spatial_ref = input_layer.GetSpatialRef()

    # Create the output shapefile
    output_driver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(output_shapefile):
        output_ds = ogr.Open(output_shapefile, update=True)
        output_layer = output_ds.GetLayerByIndex(0)
    else:
        output_ds = output_driver.CreateDataSource(output_shapefile)
        if output_ds is None:
            raise ValueError(f'Could not create output shapefile {output_shapefile}')

        # Create a new field "Site" in the output layer
        output_layer = output_ds.CreateLayer(os.path.splitext(os.path.basename(output_shapefile))[0], geom_type=ogr.wkbPolygon, srs=input_spatial_ref)
        output_layer.CreateField(ogr.FieldDefn('Site', ogr.OFTString))
        output_layer.CreateField(ogr.FieldDefn('SurveyDate', ogr.OFTString))

    file_name_pattern = re.compile(r'^(?P<site_name>[^_]+)_(?P<survey_date>\d{8})_.*')
    match = file_name_pattern.match(os.path.basename(input_shapefile))
    if match:
        site_name = match.group('site_name')
        survey_date = match.group('survey_date')
    else:
        raise ValueError(f'Could not parse site name and survey date from file name {input_shapefile}')

    print(f'File: {os.path.basename(input_shapefile)}, Site Name: {site_name}, Survey Date: {survey_date}')

    # Loop through each feature in the input layer
    input_layer = input_ds.GetLayer()
    for feature in input_layer:
        # Buffer with distance 0 converts to polygon
        polyline_geom = feature.GetGeometryRef().Clone()
        if polyline_geom.IsEmpty():
            raise ValueError(f'Polyline geometry is empty for feature {feature.GetFID()}')
        # print(f'Line length: {polyline_geom.Length()}')

        linear_ring = ogr.Geometry(ogr.wkbLinearRing)
        for idx in range(polyline_geom.GetPointCount()):
            x, y, z = polyline_geom.GetPoint(idx)
            linear_ring.AddPoint(x, y)
        linear_ring.CloseRings()
        # print(f'Ring length: {linear_ring.Length()}')

        polygon_geom = ogr.Geometry(ogr.wkbPolygon)
        polygon_geom.AddGeometry(linear_ring)
        polygon_geom.CloseRings()
        if polygon_geom.IsEmpty():
            raise ValueError(f'Polygon geometry is empty for feature {feature.GetFID()}')
        # print(f'Area {polygon_geom.GetArea()}')

        # Create a new feature in the output layer
        output_feature = ogr.Feature(output_layer.GetLayerDefn())
        output_feature.SetGeometry(polygon_geom)

        # Copy the "Site" attribute from the input feature to the output feature
        output_feature.SetField('Site', site_name)
        output_feature.SetField('SurveyDate', survey_date)

        # Add the feature to the output layer
        output_layer.CreateFeature(output_feature)
        output_feature = None

    # Clean up
    input_ds = None
    output_ds = None


def main():
    """
    Parse the script arguments and loop over each input ShapeFile in the input folder
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('input_folder', help='Folder containing campsite polygon ShapeFiles', type=str)
    parser.add_argument('output_shapefile_path', help='Path where the merged ShapeFile will be generated', type=str)
    args = parser.parse_args()

    count = 0
    for filename in os.listdir(args.input_folder):
        if filename.endswith(".shp"):
            input_shapefile = os.path.join(args.input_folder, filename)
            if input_shapefile != args.output_shapefile_path:
                convert_polyline_to_polygon(input_shapefile, args.output_shapefile_path)
                count += 1

    print(f'Conversion complete. {count} ShapeFiles merged into {args.output_shapefile_path}')


if __name__ == '__main__':
    main()
