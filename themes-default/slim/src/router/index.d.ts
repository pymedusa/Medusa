import { Vue } from 'vue/types/vue';
import { VRoute, RouteConfig } from 'vue-router';

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
 *       Use an object for `confirm` to customize the dialog from the sub menu definition.
 */
export interface SubMenuItem {
    /** Text for the menu item. */
    title: string;
    /** Target URL for the menu item. */
    path: string;
    /** Icon class for the menu item. */
    icon: string;
    /** When should this menu item be visible? (default: `undefined` = always) */
    requires?: boolean;
    /**
     * Show a confirmation dialog upon clicking the menu item.
     * The value is the type of dialog to show - configurable on the `SubMenu` component.
    */
    confirm?: string;
}

/** Sub menu definition. */
export type SubMenu = SubMenuItem[];
/** Sub menu function that returns a sub menu definition. */
export type SubMenuFunction = (vm: Vue) => SubMenu;

interface MakeLegacyRedirectParams extends RouteConfig {
    /** The target route name to redirect to. */
    target: string;
    /** The path to redirect from. */
    from: string;
    /**
     * A mapping linking path parameters on the target route
     * to a function that returns the matching query parameters' values
     * (`pathParamName: route => route.query.queryParamName`).
     */
    targetParams: {
        [pathParamName: string]: (route: VRoute) => string;
    };
}

/**
 * Make a redirection route for legacy routes that use query parameters,
 * that redirects to the main route that uses path parameters.
 *
 * @param params Redirect configuration.
 * @returns A redirection route.
 */
export const makeLegacyRedirect: (params: MakeLegacyRedirectParams) => RouteConfig;

/**
 * Make a legacy path from a route path.
 *
 * @param path Original (optionally parameterized) route path.
 * @returns Legacy path.
 */
export const extractLegacyPath: (path: string) => string;

interface LegacyRedirectWrapperParams extends RouteConfig {
    /** Redirect route configuration. */
    legacyRedirect: MakeLegacyRedirectParams;
};

/**
 * A helper to create two routes:
 *  - A redirection route for legacy routes that use query parameters,
 *    that redirects to the main route that uses path parameters.
 *    If the path to redirect from is not provided, it will extract one from the normal route's path.
 *  - A normal route as with all the options passed.
 *
 * Use with spread operator: `[ ...legacyRedirectWrapper({ ... }) ]`.
 *
 * @param params Route configuration.
 * @returns A redirection route + a normal route.
 */
export const legacyRedirectWrapper: (params: LegacyRedirectWrapperParams) => [RouteConfig, RouteConfig];
