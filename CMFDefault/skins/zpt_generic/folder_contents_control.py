## Script (Python) "folder_contents_control"
##parameters=ids=(), delta=1, items_copy='', items_cut='', items_delete='', items_new='', items_paste='', items_rename='', items_up='', items_down='', items_top='', items_bottom='', items_sort='', **kw
##title=
##
from ZTUtils import Batch
from ZTUtils import make_query
from Products.CMFCore.utils import getToolByName
from Products.CMFDefault.permissions import AddPortalContent
from Products.CMFDefault.permissions import DeleteObjects
from Products.CMFDefault.permissions import ListFolderContents
from Products.CMFDefault.permissions import ManageProperties
from Products.CMFDefault.permissions import ViewManagementScreens
from Products.CMFDefault.utils import html_marshal

mtool = getToolByName(script, 'portal_membership')
utool = getToolByName(script, 'portal_url')
portal_url = utool()


form = context.REQUEST.form
default_target = 'object/folderContents'
if items_copy and \
        context.validateItemIds(**form) and \
        context.folder_copy(**form) and \
        context.setRedirect(context, default_target, **kw):
    return
elif items_cut and \
        context.validateItemIds(**form) and \
        context.folder_cut(**form) and \
        context.setRedirect(context, default_target, **kw):
    return
elif items_delete and \
        context.validateItemIds(**form) and \
        context.folder_delete(**form) and \
        context.setRedirect(context, default_target, **kw):
    return
elif items_new and \
        context.setRedirect(context, 'object/new'):
    return
elif items_paste and \
        context.folder_paste(**form) and \
        context.setRedirect(context, default_target, **kw):
    return
elif items_rename and \
        context.validateItemIds(**form) and \
        context.setRedirect(context, 'object/rename_items', ids=ids, **kw):
    return
elif items_sort and \
        context.folder_sort(**form) and \
        context.setRedirect(context, default_target, **kw):
    return
elif items_up and \
        context.validateItemIds(**form) and \
        context.folder_up(**form) and \
        context.setRedirect(context, default_target, **kw):
    return
elif items_down and \
        context.validateItemIds(**form) and \
        context.folder_down(**form) and \
        context.setRedirect(context, default_target, **kw):
    return
elif items_top and \
        context.validateItemIds(**form) and \
        context.folder_top(**form) and \
        context.setRedirect(context, default_target, **kw):
    return
elif items_bottom and \
        context.validateItemIds(**form) and \
        context.folder_bottom(**form) and \
        context.setRedirect(context, default_target, **kw):
    return


control = {}

items_manage_allowed = mtool.checkPermission(ViewManagementScreens, context)
items_delete_allowed = mtool.checkPermission(DeleteObjects, context)
items_add_allowed = mtool.checkPermission(AddPortalContent, context)
upitems_list_allowed = mtool.checkPermission(ListFolderContents, context,
                                             'aq_parent')
items_move_allowed = mtool.checkPermission(ManageProperties, context)

up_info = {}
if upitems_list_allowed:
    up_obj = context.aq_parent
    if hasattr(up_obj, 'portal_url'):
        up_url = up_obj.getActionInfo('object/folderContents')['url']
        up_info = { 'icon': '%s/UpFolder_icon.gif' % portal_url,
                    'id': up_obj.getId(),
                    'url': up_url }
    else:
        up_info = { 'icon': '',
                    'id': 'Root',
                    'url': '' }
control['up_info'] = up_info

target = context.getActionInfo('object/folderContents')['url']

key = kw.pop('key', '')
reverse = kw.pop('reverse', 0)
if not key:
    (key, reverse) = context.getDefaultSorting()
    is_default = 1
elif (key, reverse) == context.getDefaultSorting():
    is_default = 1
else:
    kw['key'] = key
    if reverse:
        kw['reverse'] = reverse
    is_default = 0
b_start = kw.pop('b_start', 0)
if b_start:
    kw['b_start'] = b_start

columns = ( {'key': 'Type',
             'title': 'Type',
             'width': '20',
             'colspan': '2'}
          , {'key': 'getId',
             'title': 'Name',
             'width': '380',
             'colspan': None}
          , {'key': 'modified',
             'title': 'Last Modified',
             'width': '160',
             'colspan': None}
          , {'key': 'position',
             'title': 'Position',
             'width': '80',
             'colspan': None }
          )
for column in columns:
    if key == column['key'] and not reverse and key != 'position':
        query = make_query(key=column['key'], reverse=1)
    else:
        query = make_query(key=column['key'])
    column['url'] = '%s?%s' % (target, query)

context.filterCookie()
folderfilter = context.REQUEST.get('folderfilter', '')
filter = context.decodeFolderFilter(folderfilter)
items = context.listFolderContents(contentFilter=filter)
items = sequence.sort( items, ((key, 'cmp', reverse and 'desc' or 'asc'),) )
batch_obj = Batch(items, 25, b_start, orphan=0)
items = []
i = 1
for item in batch_obj:
    item_icon = item.getIcon(1)
    item_id = item.getId()
    item_position = key == 'position' and str(b_start + i) or '...'
    i += 1
    item_url = item.getActionInfo( ('object/folderContents',
                                    'object/view') )['url']
    items.append( { 'checkbox': items_manage_allowed and
                                ('cb_%s' % item_id) or '',
                    'icon': item_icon and
                            ( '%s/%s' % (portal_url, item_icon) ) or '',
                    'id': item_id,
                    'modified': item.ModificationDate(),
                    'position': item_position,
                    'title': item.Title(),
                    'type': item.Type() or None,
                    'url': item_url } )
navigation = context.getBatchNavigation(batch_obj, target, **kw)
control['batch'] = { 'listColumnInfos': tuple(columns),
                     'listItemInfos': tuple(items),
                     'navigation': navigation }

hidden_vars = []
for name, value in html_marshal(**kw):
    hidden_vars.append( {'name': name, 'value': value} )
buttons = []
if items_manage_allowed:
    if items_add_allowed and context.allowedContentTypes():
        buttons.append( {'name': 'items_new', 'value': 'New...'} )
        if items:
            buttons.append( {'name': 'items_rename', 'value': 'Rename'} )
    if items:
        buttons.append( {'name': 'items_cut', 'value': 'Cut'} )
        buttons.append( {'name': 'items_copy', 'value': 'Copy'} )
    if items_add_allowed and context.cb_dataValid():
        buttons.append( {'name': 'items_paste', 'value': 'Paste'} )
    if items_delete_allowed and items:
        buttons.append( {'name': 'items_delete', 'value': 'Delete'} )
length = batch_obj.sequence_length
is_orderable = items_move_allowed and (key == 'position') and length > 1
is_sortable = items_move_allowed and not is_default
deltas = range( 1, min(5, length) ) + range(5, length, 5)
control['form'] = { 'action': target,
                    'listHiddenVarInfos': tuple(hidden_vars),
                    'listButtonInfos': tuple(buttons),
                    'listDeltas': tuple(deltas),
                    'is_orderable': is_orderable,
                    'is_sortable': is_sortable }

return control
