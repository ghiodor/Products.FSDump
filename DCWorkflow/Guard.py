##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
# 
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
# 
##############################################################################
""" Guard conditions in a web-configurable workflow.

$Id$
"""

from string import split, strip, join
from cgi import escape

import Globals
from Globals import DTMLFile, Persistent
from AccessControl import ClassSecurityInfo
from Acquisition import Explicit, aq_base

from Products.CMFCore.CMFCorePermissions import ManagePortal

from Expression import Expression, StateChangeInfo, createExprContext
from utils import _dtmldir


class Guard (Persistent, Explicit):
    permissions = ()
    roles = ()
    groups = ()
    expr = None

    security = ClassSecurityInfo()
    security.declareObjectProtected(ManagePortal)

    guardForm = DTMLFile('guard', _dtmldir)

    def check(self, sm, wf_def, ob):
        '''
        Checks conditions in this guard.
        '''
        if self.permissions:
            for p in self.permissions:
                if sm.checkPermission(p, ob):
                    break
            else:
                return 0
        if self.roles:
            # Require at least one of the given roles.
            u_roles = sm.getUser().getRolesInContext(ob)
            for role in self.roles:
                if role in u_roles:
                    break
            else:
                return 0
        if self.groups:
            # Require at least one of the specified groups.
            u = sm.getUser()
            if hasattr(aq_base(u), 'getContextualGroupMonikers'):
                u_groups = u.getContextualGroupMonikers(ob)
            else:
                u_groups = ()
            for group in self.groups:
                if ('(Group) %s' % group) in u_groups:
                    break
            else:
                return 0
        expr = self.expr
        if expr is not None:
            econtext = createExprContext(StateChangeInfo(ob, wf_def))
            res = expr(econtext)
            if not res:
                return 0
        return 1

    security.declareProtected(ManagePortal, 'getSummary')
    def getSummary(self):
        # Perhaps ought to be in DTML.
        res = []
        if self.permissions:
            res.append('Requires permission:')
            res.append(formatNameUnion(self.permissions))
        if self.roles:
            if res:
                res.append('<br/>')
            res.append('Requires role:')
            res.append(formatNameUnion(self.roles))
        if self.groups:
            if res:
                res.append('<br/>')
            res.append('Requires group:')
            res.append(formatNameUnion(self.groups))
        if self.expr is not None:
            if res:
                res.append('<br/>')
            res.append('Requires expr:')
            res.append('<code>' + escape(self.expr.text) + '</code>')
        return join(res, ' ')

    def changeFromProperties(self, props):
        '''
        Returns 1 if changes were specified.
        '''
        if props is None:
            return 0
        res = 0
        s = props.get('guard_permissions', None)
        if s:
            res = 1
            p = map(strip, split(s, ';'))
            self.permissions = tuple(p)
        s = props.get('guard_roles', None)
        if s:
            res = 1
            r = map(strip, split(s, ';'))
            self.roles = tuple(r)
        s = props.get('guard_groups', None)
        if s:
            res = 1
            r = map(strip, split(s, ';'))
            self.groups = tuple(r)
        s = props.get('guard_expr', None)
        if s:
            res = 1
            self.expr = Expression(s)
        return res

    security.declareProtected(ManagePortal, 'getPermissionsText')
    def getPermissionsText(self):
        if not self.permissions:
            return ''
        return join(self.permissions, '; ')

    security.declareProtected(ManagePortal, 'getRolesText')
    def getRolesText(self):
        if not self.roles:
            return ''
        return join(self.roles, '; ')

    security.declareProtected(ManagePortal, 'getGroupsText')
    def getGroupsText(self):
        if not self.groups:
            return ''
        return join(self.groups, '; ')

    security.declareProtected(ManagePortal, 'getExprText')
    def getExprText(self):
        if not self.expr:
            return ''
        return str(self.expr.text)

Globals.InitializeClass(Guard)


def formatNameUnion(names):
    escaped = ['<code>' + escape(name) + '</code>' for name in names]
    if len(escaped) == 2:
        return ' or '.join(escaped)
    elif len(escaped) > 2:
        escaped[-1] = ' or ' + escaped[-1]
    return '; '.join(escaped)
