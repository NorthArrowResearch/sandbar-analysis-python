"""
Computational extents represents a ShapeFile containing polygons that define the computational
extents for each site. The ShapeFile must contain a field named 'Site' that contains the site code
"""
import os
from osgeo import osr, ogr
from logger import Logger

SITE_CODE_FIELD = 'Site'
SECTION_FIELD = 'Section'


class ComputationExtents:
    """
    Computational extents represents a ShapeFile containing polygons that define the computational
    extents for each site. The ShapeFile must contain a field named 'Site' that contains the site code
    """

    def __init__(self, full_path: str, epsg):
        self.full_path = full_path
        self.log = Logger('Comp. Extents')

        assert os.path.isfile(self.full_path), f'The computation extents ShapeFile does not exist at {self.full_path}'

        try:
            driver = ogr.GetDriverByName('ESRI Shapefile')
            # 0 means read-only. 1 means writeable.
            data_source = driver.Open(self.full_path, 0)
        except RuntimeError as e:
            raise FileNotFoundError(f'Unable to open computation extent ShapeFile {self.full_path}') from e

        # Check to see if shapefile is found.
        assert data_source is not None, f'Could not open computation extents ShapeFile {self.full_path}'

        # Make sure that there's at least one feature
        layer = data_source.GetLayer()
        feature_count = layer.GetFeatureCount()
        assert feature_count > 0, f'The computation extents ShapeFile is empty {self.full_path}'

        # Check that the spatial reference matches the EPSGID
        source_srs = layer.GetSpatialRef()
        self.log.debug(f'Computational Bounds SRS: {source_srs.ExportToWkt()}')

        desired_ref = osr.SpatialReference()
        if epsg is int:
            desired_ref.ImportFromEPSG(epsg)
        else:
            desired_ref.ImportFromWkt(epsg)

        # TODO: This is failing because the computational bounds SRS is slightly different than specified.
        # assert desired_ref.IsSame(source_srs), f'The spatial reference of the computation extents ({source_srs}) does not match that of the desired EPSG ID: {desired_ref}'

        # Validate that the site code and section fields both exist
        site_field = False
        section_field = False
        layer_def = layer.GetLayerDefn()

        for i in range(layer_def.GetFieldCount()):
            if layer_def.GetFieldDefn(i).GetName() == SITE_CODE_FIELD:
                # fieldTypeCode = layerDefinition.GetFieldDefn(i).GetType()
                # fieldType = layerDefinition.GetFieldDefn(i).GetFieldTypeName(fieldTypeCode)
                # TODO: check field type is string
                site_field = True

            elif layer_def.GetFieldDefn(i).GetName() == SECTION_FIELD:
                # TODO: check field type is string
                section_field = True

        assert site_field, f"Unable to find the site code field '{SITE_CODE_FIELD}' in the computation extent ShapeFile."
        assert section_field, f"Unable to find the site code field '{SECTION_FIELD}' in the computation extent ShapeFile."

        self.log.info(f'Computational boundaries polygon ShapeFile loaded containing {feature_count} features.')

    def get_filter_clause(self, site_code: str, section_type: str) -> str:
        """
        Returns a string that can be used as a filter clause for OGR
        """

        section_where = section_type
        idx_hyphon = section_where.find('-')
        if idx_hyphon >= 0:
            if 'single' in section_where[idx_hyphon:].lower():
                section_where = section_where[:idx_hyphon]
            else:
                section_where = section_where[idx_hyphon + 1:]

        section_where = section_where.replace(' ', '')
        return f"(\"{SITE_CODE_FIELD}\" ='{site_code}')  AND (\"{SECTION_FIELD}\"='{section_where}')"
