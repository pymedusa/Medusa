// eslint-disable-next-line valid-jsdoc
/** @type {import('.').makeLegacyRedirect} */
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

// eslint-disable-next-line valid-jsdoc
/** @type {import('.').extractLegacyPath} */
const extractLegacyPath = path => {
    const pos = path.indexOf(':');
    const legacyPath = pos === -1 ? path : path.slice(0, pos - 1);
    return legacyPath.endsWith('/') ? legacyPath.slice(0, -1) : legacyPath;
};

// eslint-disable-next-line valid-jsdoc
/** @type {import('.').legacyRedirectWrapper} */
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
