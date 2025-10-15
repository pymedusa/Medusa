'''
Simple decorator to set attributes of target function or class in a DRY way.

Usage example:

    # Django proposes:
    def my_calculated_field(...
    my_calculated_field.short_description = 'Field'
    my_calculated_field.admin_order_field = 'real_field'

    # DRY:
    @attr(short_description='Field', admin_order_field='real_field')
    def my_calculated_field(...

Get it:

    sudo pip install attr
    from attr import attr

New popular http://attrs.org used by https://pytest.org defines another "attr" package that shadows this "attr" module.
Please use "dry_attr" alias to unshadow it:

    from dry_attr import attr
    from dry_attr import dry_attr

attr version 0.3.2
Copyright (C) 2013-2022 by Denis Ryzhkov <denisr@denisr.com>
MIT License
'''

def attr(**names_values):
    def set_target(target):
        for name, value in names_values.items():
            setattr(target, name, value)
        return target
    return set_target

dry_attr = attr

def test():

    @attr(a=1, b=2)
    def f(): pass

    @attr(a=1, b=2)
    class C(object): pass

    assert f.a == C.a == 1
    assert f.b == C.b == 2

    print('OK')

if __name__ == '__main__':
    test()
