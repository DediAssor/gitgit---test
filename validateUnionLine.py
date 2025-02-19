# -*- coding: utf-8 -*-
import os
import arcpy
import arcpy.management

#TOOL PARAMETERS
debug_mode = False
if debug_mode:
    #debug parameters
    input_workspace = r'C:\Users\Dedi\Desktop\עבודה\My GIS\דשא\מרץ 2024\March 2024\sandbox3.gdb'
    input_stands = os.path.join(input_workspace, 'FinalStands')
    input_unionLine = os.path.join(input_workspace, 'linee')
else:
    input_stands = arcpy.GetParameter(0)
    #Take all the features, even if layar has selection.
    input_stands = arcpy.Describe(input_stands).catalogPath

    input_unionLine = arcpy.GetParameter(1)
    #Take all the features, even if layar has selection.
    input_unionLine = arcpy.Describe(input_unionLine).catalogPath

#input_workspace = r'C:\Users\Dedi\Desktop\עבודה\My GIS\דשא\מרץ 2024\March 2024\sandbox3.gdb'
memo_workspace = 'memory'
arcpy.env.workspace = memo_workspace
#@later - change inputworkspace into in_memowwww~~~
arcpy.env.overwriteOutput = True

#feature classes:
endpoints_fc = os.path.join(memo_workspace, 'endpoints')
endpoints_sj_fc = os.path.join(memo_workspace, 'endpoints_sj')
neighborsTable = os.path.join(memo_workspace, 'neighbors')

input_unionLine_oidFieldName = arcpy.Describe(input_unionLine).oidFieldName
input_stands_oidFieldName = arcpy.Describe(input_stands).oidFieldName

#functions:
def areNeighbors(oidList, nbrTable):
    """
    Takes a list of two objectid's and check if they appear
    as neighbors in the neighbors table (created by the tool "polygon neighbors")
    """
    table_workspace = arcpy.Describe(nbrTable).path
    field_0_name = 'src_OBJECTID'
    field_0_delimited = arcpy.AddFieldDelimiters(table_workspace, field_0_name)
    value_0 = oidList[0]

    field_1_name = 'nbr_OBJECTID'
    field_1_delimited = arcpy.AddFieldDelimiters(table_workspace, field_1_name)
    value_1 = oidList[1]

    #src_OBJECTID = 18 And nbr_OBJECTID = 165

    sql_exp = """{0} = {1} AND {2} = {3}""".format(field_0_delimited, value_0, field_1_delimited, value_1)
    sc_temp = arcpy.da.SearchCursor(nbrTable,'OID@',sql_exp)
    try:
        sc_temp.next()
    except StopIteration:
        found = False
    else:
        found = True
    del sc_temp
    return found



"""
@
IMPORT FIELDS.XLSX!!!
@
"""

#0 - create beighbor polygons table:
arcpy.analysis.PolygonNeighbors(
    in_features=input_stands,
    out_table=neighborsTable,
    in_fields=input_stands_oidFieldName,
    area_overlap="NO_AREA_OVERLAP",
    both_sides="BOTH_SIDES",
    cluster_tolerance=None,
    out_linear_units="METERS",
    out_area_units="SQUARE_METERS"
)

#1 - line to first and last points:
arcpy.management.GeneratePointsAlongLines(
    Input_Features=input_unionLine,
    Output_Feature_Class=endpoints_fc,
    Point_Placement="PERCENTAGE",
    Distance=None,
    Percentage=100,
    Include_End_Points="END_POINTS",
    Add_Chainage_Fields="NO_CHAINAGE"
)

#2 - spatial join w/field mapping
#2.1 - field mapping:
for useless_index in [1]:
    fms = arcpy.FieldMappings()

    fm_stand_objectID = arcpy.FieldMap()
    #@CHANGE FIELDS TO SMALL-FIELD OBJECTS.
    fm_stand_objectID.addInputField(input_stands, input_stands_oidFieldName)
    fm_stand_objectID_outfield = fm_stand_objectID.outputField
    fm_stand_objectID_outfield.name = "stand_objectid"
    fm_stand_objectID_outfield.aliasName = "stand_objectid"
    fm_stand_objectID.outputField = fm_stand_objectID_outfield
    fms.addFieldMap(fm_stand_objectID)

    fm_stand_standNumber = arcpy.FieldMap()
    fm_stand_standNumber.addInputField(input_stands, "stand_no")
    #fm_stand_standNumber_outfield = fm_stand_standNumber.outputField
    #fm_stand_standNumber_outfield.name = "stand_no"
    #fm_stand_standNumber_outfield.aliasName = "stand_no"
    #fm_stand_standNumber.outputField = fm_stand_standNumber_outfield
    fms.addFieldMap(fm_stand_standNumber)

    fm_stand_helkaNumber = arcpy.FieldMap()
    fm_stand_helkaNumber.addInputField(input_stands, "helka")
    #fm_stand_helkaNumber_outfield = fm_stand_helkaNumber.outputField
    #fm_stand_helkaNumber_outfield.name = "helka"
    #fm_stand_helkaNumber_outfield.aliasName = "helka"
    #fm_stand_helkaNumber.outputField = fm_stand_helkaNumber_outfield
    fms.addFieldMap(fm_stand_helkaNumber)

    fm_line_objectID = arcpy.FieldMap()
    #input_unionLine_oidFieldName = arcpy.Describe(input_unionLine).oidFieldName
    fm_line_objectID.addInputField(endpoints_fc, "orig_fid")
    fm_line_objectID_outfield = fm_line_objectID.outputField
    fm_line_objectID_outfield.name = "line_objectid"
    fm_line_objectID_outfield.aliasName = "line_objectid"
    fm_line_objectID.outputField = fm_line_objectID_outfield
    fms.addFieldMap(fm_line_objectID)

arcpy.analysis.SpatialJoin(
    target_features=endpoints_fc,
    join_features=input_stands,
    out_feature_class=endpoints_sj_fc,
    join_operation="JOIN_ONE_TO_ONE",
    join_type="KEEP_ALL",
    field_mapping=fms,
    match_option="INTERSECT",
    search_radius=None,
    distance_field_name="",
    match_fields=None
)

#3 - create result fields
outputFields = [
    ('status', 15),
    ('notes', 2000)
]
unionLine_fields = arcpy.ListFields(input_unionLine)
unionLine_fields_names = [f.name.lower() for f in unionLine_fields]
for fieldTup in outputFields:
    fieldName = fieldTup[0]
    fieldLength = fieldTup[1]
    if fieldName.lower() in unionLine_fields_names:
        arcpy.management.DeleteField(input_unionLine, fieldName)
    arcpy.management.AddField(input_unionLine, fieldName, 'String', field_length=fieldLength)


#4 - iterate lines
uc_line = arcpy.da.UpdateCursor(
    input_unionLine,
    field_names= ['OID@'] + [tup[0] for tup in outputFields]
    )


line_objectid_field_delimited = arcpy.AddFieldDelimiters(
    arcpy.Describe(endpoints_sj_fc).path,
    "line_objectid"
    )

for r_line in uc_line:
    line_objectid = r_line[0]
    
    #sql for endpoints_sj_fc by lineobjectid
    query_exp = """{0} = {1}""".format(line_objectid_field_delimited, line_objectid)
    query_fields = ["helka", "stand_no", "stand_objectid"]
    sc_endpoints_sj = arcpy.da.SearchCursor(
        endpoints_sj_fc,
        query_fields,
        where_clause=query_exp
    )
    points = []
    for r_endpoints_sj in sc_endpoints_sj:
        points.append(r_endpoints_sj)
    del sc_endpoints_sj
    
    #check: 1)same helka; 2)different stand; 3)stands are neighbors:
    errors = []
    #1)same helka
    helka_0 = points[0][0]
    helka_1 = points[1][0]
    if helka_0 != helka_1:
        error_txt = "Different helka (%s,%s)" % (helka_0, helka_1)
        errors.append(error_txt)
    #2) different stand
    stand_0 = points[0][1]
    stand_1 = points[1][1]
    if stand_0 == stand_1:
        error_txt = "Same stand %s" % stand_0
        errors.append(error_txt)
    #3)stands are neighbors:
    stand_objectid_0 = points[0][2]
    stand_objectid_1 = points[1][2]
    if not areNeighbors([stand_objectid_0, stand_objectid_1], neighborsTable):
        error_txt = "Stands are not neighbors (%s,%s)" % (stand_objectid_0, stand_objectid_1)
        errors.append(error_txt)
    
    #add notes + set status accordingly:
    if errors:
        notes = '. '.join(errors)
        status = 'Error'
        #add warnings accordingly
        warning_txt = '(%s: %s) Errors found: %s' % (input_unionLine_oidFieldName, line_objectid, notes)
        arcpy.AddWarning(warning_txt)
    else:
        notes = None
        status = 'Okay'
    
    #update the row:
    r_line[1] = status
    r_line[2] = notes
    
    #r_line.setValue(outputFields[0][0], status)
    #r_line.setValue(outputFields[1][0], notes)
    uc_line.updateRow(r_line)

del uc_line
#arcpy.management.delete.....
arcpy.management.Delete(endpoints_fc)
arcpy.management.Delete(endpoints_sj_fc)
arcpy.management.Delete(neighborsTable)
print('done')