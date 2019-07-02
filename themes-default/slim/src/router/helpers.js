/**
 * Make a redirection route for legacy routes that use query parameters,
 * that redirects to the main route that uses path parameters.
 *
 * @param {Object<string, any>} params Redirect configuration.
 * @param {string} params.target The target route name to redirect to.
 * @param {string} params.from The path to redirect from.
 * @param {Object<string, function>} [params.targetParams]
 *      A mapping linking path parameters on the target route
 *      to a function that returns the matching query parameters' values
 *      (`pathParamName: route => route.query.queryParamName`).
 * @param {...Object<string, any>} params.config Extra route config options.
 * @returns {Object<string, any>} A redirection route.
 */
export const makeLegacyRedirect = ({ target, from, targetParams, ...config }) => ({
    name: `${target}-legacy`,
    path: from,
    redirect: to => ({
        name: target,
        params: Object.entries(targetParams).reduce(
            (params, [path, query]) => Object.assign(params, { [path]: query(to) }),
            {}
        ),
        query: {}
    }),
    ...config
});

/**
 * Make a legacy path from a route path.
 *
 * @param {string} path Original (optionally parameterized) route path.
 * @returns {string} Legacy path.
 */
const extractLegacyPath = path => {
    const pos = path.indexOf(':');
    const legacyPath = pos === -1 ? path : path.substring(0, pos - 1);
    return legacyPath.endsWith('/') ? legacyPath.slice(0, -1) : legacyPath;
};

/**
 * A helper to create two routes:
 *  - A redirection route for legacy routes that use query parameters,
 *    that redirects to the main route that uses path parameters.
 *  - A normal route as with all the options passed.
 * Use with spread operator: `[ ...legacyRedirectWrapper({ ... }) ]`.
 *
 * @param {Object<string, any>} params Route configuration.
 * @param {Object<string, any>} params.legacyRedirect Redirect route configuration.
 * @param {string} [params.legacyRedirect.from]
 *      The path to redirect from. If not provided, will extract one from the normal route's path.
 * @param {Object<string, function>} [params.legacyRedirect.targetParams]
 *      A mapping linking path parameters on the target route
 *      to a function that returns the matching query parameters' values
 *      (`pathParamName: route => route.query.queryParamName`).
 * @param {...Object<string, any>} [params.legacyRedirect.redirectConfig] Extra redirect route config options.
 * @param {...Object<string, any>} params.routeConfig Original route config options.
 * @returns {Object<string, any>[]} A redirection route + a normal route.
 */
export const legacyRedirectWrapper = params => {
    const { legacyRedirect, ...routeConfig } = params;
    const {
        from = extractLegacyPath(routeConfig.path),
        targetParams,
        ...redirectConfig
    } = legacyRedirect;

    const redirectRoute = makeLegacyRedirect({
        target: routeConfig.name,
        from,
        targetParams,
        ...redirectConfig
    });

    return [
        redirectRoute,
        routeConfig
    ];
};
