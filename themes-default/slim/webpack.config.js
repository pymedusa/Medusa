const path = require('path');
const { ProvidePlugin } = require('webpack');
const VueLoaderPlugin = require('vue-loader/lib/plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const pkg = require('./package.json');

const { cssThemes } = pkg.config;

/**
 * Helper function to queue actions for each theme.
 * @param {function} action - Receives the `theme` object as a parameter. Should return an object.
 * @returns {Object[]} - The actions for each theme.
 */
const perTheme = action => Object.values(cssThemes).map(theme => action(theme));

/**
 * Helper function to simplify CopyWebpackPlugin configuration when copying assets from `./dist`.
 * To be used in-conjunction-with `perTheme`.
 * @param {string} type - Asset type (e.g. `js`, `css`, `fonts`). Must be the same as the folder name in `./dist`.
 * @param {string} [search] - Glob-like string to match files. (default: `**`)
 * @returns {function} - A function the recieves the theme object from `perTheme`.
 */
const copyAssets = (type, search = '**') => {
    return theme => ({
        context: './dist/',
        from: `${type}/${search}`,
        to: path.resolve(theme.dest, 'assets')
    });
};

/**
 * Make a `package.json` for a theme.
 * @param {string} themeName - Theme name
 * @param {string} currentContent - Current package.json contents
 * @returns {string} - New content
 */
const makeThemeMetadata = (themeName, currentContent) => {
    const { version, author } = JSON.parse(currentContent);
    return JSON.stringify({
        name: themeName,
        version,
        author
    }, undefined, 2);
};

const webpackConfig = mode => ({
    devtool: mode === 'production' ? 'source-map' : 'eval',
    entry: {
        // Exports all window. objects for mako files
        index: path.resolve(__dirname, 'src/index.js'),
        // Main Vue app
        app: path.resolve(__dirname, 'src/app.js')
    },
    output: {
        filename: 'js/[name].js',
        path: path.resolve(__dirname, 'dist')
    },
    resolve: {
        extensions: ['.js', '.vue', '.json'],
        alias: {
            vue$: 'vue/dist/vue.esm.js'
        }
    },
    performance: {
        hints: false
    },
    stats: {
        // Hides assets copied from `./dist` to `../../themes` by CopyWebpackPlugin
        excludeAssets: /(\.\.\/)+themes\/.*/,
        // When `false`, hides extra information about assets collected by children (e.g. plugins)
        children: false
    },
    optimization: {
        runtimeChunk: {
            name: 'vendors'
        },
        splitChunks: {
            chunks: 'all',
            name: 'vendors',
            cacheGroups: {
                styles: {
                    test: /\.css$/,
                    priority: 10
                },
                // These are the default cacheGroups!
                vendors: {
                    test: /[\\/]node_modules[\\/]/,
                    priority: -10
                },
                default: {
                    minChunks: 2,
                    priority: -20,
                    reuseExistingChunk: true
                }
            }
        }
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                use: [{
                    loader: 'vue-loader',
                    options: {
                        // This is a workaround because vue-loader can't get the webpack mode
                        productionMode: mode === 'production'
                    }
                }]
            },
            {
                test: /\.js$/,
                loader: 'babel-loader'
            },
            {
                // This rule may get either actual `.css` files or the style blocks from `.vue` files.
                // Here we delegate each request to use the appropriate loaders.
                test: /\.css$/,
                oneOf: [
                    {
                        // Handle style blocks in `.vue` files
                        // Based on this query: https://github.com/vuejs/vue-loader/blob/v15.2.7/lib/codegen/styleInjection.js#L27
                        resourceQuery: /^\?vue&type=style/,
                        use: [
                            'vue-style-loader',
                            'css-loader'
                        ]
                    },
                    {
                        // Handle regular `.css` files
                        use: [
                            {
                                loader: MiniCssExtractPlugin.loader,
                                options: {
                                    // Fixes loading fonts from the fonts folder
                                    publicPath: '../'
                                }
                            },
                            'css-loader'
                        ]
                    }
                ]
            },
            {
                test: /\.(woff2?|ttf|eot|svg)$/,
                use: [{
                    loader: 'file-loader',
                    options: {
                        name: '[name].[ext]',
                        outputPath: 'fonts'
                    }
                }]
            }
        ]
    },
    plugins: [
        // This fixes Bootstrap being unable to use jQuery
        new ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery'
        }),
        new VueLoaderPlugin(),
        new MiniCssExtractPlugin({
            filename: 'css/[name].css'
        }),
        // Queue operations for each theme
        new CopyWebpackPlugin([
            ...perTheme(copyAssets('js')),
            ...perTheme(copyAssets('css')),
            ...perTheme(copyAssets('fonts')),
            // Templates
            ...perTheme(theme => ({
                context: './views/',
                from: '**',
                to: path.resolve(theme.dest, 'templates')
            })),
            // Create package.json
            ...perTheme(theme => ({
                from: 'package.json',
                to: path.resolve(theme.dest, 'package.json'),
                toType: 'file',
                transform: content => makeThemeMetadata(theme.name, content)
            })),
            // Root files: index.html
            ...perTheme(theme => ({
                from: 'index.html',
                to: path.resolve(theme.dest),
                toType: 'dir'
            })),
            // Old JS files
            ...perTheme(theme => ({
                context: './static/',
                from: 'js/**',
                to: path.resolve(theme.dest, 'assets')
            })),
            // Old CSS files
            ...perTheme(theme => ({
                context: './static/',
                from: 'css/**',
                // Ignore theme-specific files as they are handled by the next entry
                ignore: ['css/dark.css', 'css/light.css'],
                to: path.resolve(theme.dest, 'assets')
            })),
            // Old CSS files - themed.css
            ...perTheme(theme => ({
                from: `static/css/${theme.css}`,
                to: path.resolve(theme.dest, 'assets', 'css', 'themed.css'),
                toType: 'file'
            }))
        ])
    ]
});

module.exports = (_env, argv) => webpackConfig(argv.mode);
