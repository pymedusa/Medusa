import { Vue } from 'vue/types/vue';
import { RouteConfig } from 'vue-router';

/**
 * A route config.
 */
export interface Route extends RouteConfig {
    /** Route meta fields. */
    meta?: {
        /** Page title. */
        title?: string;
        /** Page header. */
        header?: string;
        /** The name of the top-level button to highlight on AppHeader when this is the current route. */
        topMenu?: string;
        /** A definition of SubMenu for this route. */
        subMenu?: SubMenu | SubMenuFunction;
        /** Is this route fully converted to VueRouter from Mako? */
        converted?: boolean;
    }
}

/**
 * A sub menu item.
 *
 * Use a function that returns an array of sub menu items if you need access to `$store`/`$route`/etc,
 * for setting any of the properties of a menu item.
 *
 * TODO: A possible improvement:
 *       Use a object for `confirm` to customize the dialog from the sub menu definition.
 */
export interface SubMenuItem {
    /** Text for the menu item. */
    title: string;
    /** Target URL for the menu item. */
    path: string;
    /** Icon for the menu item. */
    icon: string;
    /** When should this menu item be visible? (default: `undefined` = always) */
    requires?: boolean;
    /**
     * Show a confirmation dialog upon clicking the menu item.
     * The value is the type of dialog to show - configurable on the `SubMenu` component.
    */
    confirm?: string;
}

export type SubMenu = SubMenuItem[];
export type SubMenuFunction = (vm: Vue) => SubMenu;
