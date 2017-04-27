###############################################################
#    Travel Agent Management for Openerp
#    copyright (c) 2017 Shen Xu, carlos.rollend@gmail.com
###############################################################

{
    'name':'Travel Agent Management',
    'version':'0.1', 
    'category': '',
    'description': """ This module provide an interface to manage agent orders. Working with a web front-end.
        """,
    'author': 'Shen Xu',
    'depends': ['base'], 
    'init_xml': [],
    'update_xml': [
        'tam_view.xml',
        'tam_menu.xml',
        'wizard/tam_procedure.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    
}