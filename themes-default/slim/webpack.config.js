const path = require('path');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const { ProvidePlugin } = require('webpack');
const VueLoaderPlugin = require('vue-loader/lib/plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const FileManagerPlugin = require('filemanager-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin');
const TerserJSPlugin = require('terser-webpack-plugin');

const pkg = require('./package.json');

class Theme {
    /**
     * @param {Object.<string, any>} theme Theme object.
     * @param {string} theme.name Theme name.
     * @param {string} theme.css Theme CSS file name.
     * @param {string} theme.dest Relative path to theme root folder.
     */
    constructor({ name, css, dest }) {
        this.name = name;
        this.css = css;
        this.dest = dest;
    }

    /**
     * Make a `package.json` for a theme.
     *
     * @param {string} currentContent Current package.json contents
     * @returns {string} New content
     */
    makeMetadata(currentContent) {
        const { name } = this;
        const { version, author } = JSON.parse(currentContent);
        return JSON.stringify({
            name,
            version,
            author
        }, undefined, 2);
    }
}

/**
 * Receives the `theme` object as a parameter.
 *
 * @callback action
 * @param {Theme} theme Theme object.
 * @returns {*} Return value for the provided `theme` object.
*/

/**
 * Helper function to simplify FileManagerPlugin configuration when copying assets from `./dist`.
 * To be used in-conjunction-with `perTheme`.
 *
 * @param {string} type Asset type (e.g. `js`, `css`, `fonts`). Must be the same as the folder name in `./dist/{theme.name}`.
 * @param {string} [search=**] Glob-like string to match files. (default: `**`)
 * @returns {action} A function that receives the theme object from `perTheme` as a parameter,
 *                   and returns a `FileManagerPlugin.onEnd.copy` item.
 */
const copyAssets = (type, search = '**') => {
    return theme => ({
        source: `./dist/${type}/${search}`,
        destination: path.resolve(theme.dest, 'assets', type)
    });
};

/**
 * @type {Theme[]} All the themes described on `package.json`.
 */
const cssThemes = pkg.config.cssThemes.map(theme => new Theme(theme));

/**
 * Helper function to queue actions for each theme.
 *
 * @param {action} action Receives the `theme` object as a parameter. Should return an object.
 * @returns {Object.<string, any>[]} The actions for each theme.
 */
const perTheme = action => cssThemes.map(theme => action(theme));

/**
 * Generate the Webpack configuration object.
 *
 * @param {*} env The environment data, as passed from the `--env` command line argument.
 * @param {*} mode The mode, as passed from the `--mode` command line argument.
 * @returns {Object.<string, any>} Webpack configuration object.
 */
const webpackConfig = (env, mode) => ({
    devtool: mode === 'production' ? 'source-map' : 'eval',
    entry: {
        // Exports all `window` objects for mako files
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
        excludeAssets: /(\.\.[/\\])+themes[/\\].*/,
        // When `false`, hides extra information about assets collected by children (e.g. plugins)
        children: false
    },
    optimization: {
        runtimeChunk: {
            name: 'vendors'
        },
        minimizer: [
            // Minify js files:
            // (TerserJS is webpack default minifier but we have to specify it explicitly
            // as soon as we include more minifiers)
            new TerserJSPlugin({}),
            // Minify css files:
            new OptimizeCssAssetsPlugin({})
        ],
        splitChunks: {
            chunks: 'all',
            maxInitialRequests: Infinity,
            minSize: 0,
            cacheGroups: {
                runtime: {
                    name: 'medusa-runtime',
                    test: /[/\\]src[/\\]/,
                    minChunks: 2,
                    priority: 0,
                    reuseExistingChunk: true
                },
                'date-fns': {
                    name: 'vendors~date-fns',
                    test: /[/\\]node_modules[/\\]date-fns[/\\]/,
                    priority: -5
                },
                vendors: {
                    name: 'vendors',
                    test: /[/\\](vendor|node_modules)[/\\]/,
                    priority: -10
                },
                default: {
                    name: 'vendors',
                    minChunks: 2,
                    priority: -20,
                    reuseExistingChunk: true
                }
            }
        }
    },
    module: {
        noParse: [
            // No need to parse jQuery, because it doesn't have any imports
            require.resolve('jquery')
        ],
        rules: [
            {
                test: /\.vue$/,
                loader: 'vue-loader',
                options: {
                    // This is a workaround because vue-loader can't get the webpack mode
                    productionMode: mode === 'production'
                }
            },
            {
                test: /\.js$/,
                exclude: /[/\\]node_modules[/\\]/,
                loader: 'babel-loader',
                options: {
                    cacheDirectory: mode !== 'production'
                }
            },
            {
                // This rule may get either actual `.css` files or the style blocks from `.vue` files.
                // Here we delegate each request to use the appropriate loaders.
                test: /\.css$/,
                oneOf: [
                    // Handle style blocks in `.vue` files
                    {
                        resourceQuery: /^\?vue&type=style/,
                        use: [
                            'vue-style-loader',
                            {
                                loader: 'css-loader',
                                options: {
                                    esModule: false
                                }
                            }
                        ]
                    },
                    // Handle regular `.css` files
                    {
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
                loader: 'file-loader',
                options: {
                    name: '[name].[ext]',
                    outputPath: 'fonts'
                }
            }
        ]
    },
    plugins: [
        new CleanWebpackPlugin(),
        // This fixes Bootstrap being unable to use jQuery
        new ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery'
        }),
        new VueLoaderPlugin(),
        new MiniCssExtractPlugin({
            filename: 'css/[name].css'
        }),
        // Copy bundled assets for each theme
        // Only use for assets emitted by Webpack.
        new FileManagerPlugin({
            onEnd: {
                copy: [
                    ...perTheme(copyAssets('js')),
                    ...perTheme(copyAssets('css')),
                    ...perTheme(copyAssets('fonts'))
                ]
            }
        }),
        // Copy static files for each theme
        // Don't use for assets emitted by Webpack because this plugin runs before the bundle is created.
        new CopyWebpackPlugin({
            patterns: [
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
                    transform: content => theme.makeMetadata(content)
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
                    to: path.resolve(theme.dest, 'assets'),
                    globOptions: {
                        // Ignore theme-specific files as they are handled by the next entry
                        ignore: cssThemes.map(theme => `**/css/${theme.css}`)
                    }
                })),
                // Old CSS files - themed.css
                ...perTheme(theme => ({
                    from: `static/css/${theme.css}`,
                    to: path.resolve(theme.dest, 'assets', 'css', 'themed.css'),
                    toType: 'file'
                }))
            ]
        })
    ]
});

/**
 * See: https://webpack.js.org/configuration/configuration-types/#exporting-a-function
 *
 * @param {*} env An environment. See the environment options CLI documentation for syntax examples.
 * @param {*} argv An options map (argv). This describes the options passed to webpack, with keys such as output-filename and optimize-minimize.
 * @returns {Object.<string, any>} Webpack configuration object.
 */
module.exports = (env = {}, argv = {}) => webpackConfig(env, argv.mode || process.env.NODE_ENV);
