const path = require('path');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const { NormalModuleReplacementPlugin, ProvidePlugin } = require('webpack');
const VueLoaderPlugin = require('vue-loader/lib/plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const FileManagerPlugin = require('filemanager-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const OptimizeCssAssetsPlugin = require('optimize-css-assets-webpack-plugin');

const pkg = require('./package.json');

// Verify that `loadsh/noop` is available
require.resolve('lodash/noop');

const { cssThemes } = pkg.config;

/**
 * Helper function to simplify FileManagerPlugin configuration when copying assets from `./dist`.
 *
 * @param {object} theme Theme object.
 * @param {string} theme.name Theme name.
 * @param {string} theme.css Theme CSS file name.
 * @param {string} theme.dest Relative path to theme root folder.
 * @param {string} type Asset type (e.g. `js`, `css`, `fonts`). Must be the same as the folder name in `./dist/{theme.name}`.
 * @param {string} [search=**] Glob-like string to match files. (default: `**`)
 * @returns {object} A `FileManagerPlugin.onEnd.copy` item.
 */
const copyAssets = (theme, type, search = '**') => ({
    source: `./dist/${theme.name}/${type}/${search}`,
    destination: path.resolve(theme.dest, 'assets', type)
});

/**
 * Make a `package.json` for a theme.
 *
 * @param {string} themeName Theme name
 * @param {string} currentContent Current package.json contents
 * @returns {string} New content
 */
const makeThemeMetadata = (themeName, currentContent) => {
    const { version, author } = JSON.parse(currentContent);
    return JSON.stringify({
        name: themeName,
        version,
        author
    }, undefined, 2);
};

/**
 * Generate a Webpack configuration object for a theme.
 *
 * @param {object} opts Config options.
 * @param {object} opts.theme Theme object.
 * @param {string} opts.theme.name Theme name.
 * @param {string} opts.theme.css Theme CSS file name.
 * @param {string} opts.theme.dest Relative path to theme root folder.
 * @param {boolean} opts.isProd Is this a production build?
 * @param {boolean} opts.stats Print extra build stats?
 * @returns {object} Webpack configuration object.
 */
const makeConfig = ({ theme, isProd, stats }) => ({
    name: theme.name,
    devtool: isProd ? 'source-map' : 'eval',
    entry: {
        // Exports all `window` objects for mako files
        index: path.resolve(__dirname, 'src/index.js'),
        // Main Vue app
        app: path.resolve(__dirname, 'src/app.js')
    },
    output: {
        filename: 'js/[name].js',
        path: path.resolve(__dirname, 'dist', theme.name)
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
        excludeAssets: [
            /^(\.\.[\\/])+themes[\\/].*/,
            // Use `--env.stats` to show these assets
            ...(stats ? [] : [
                /^fonts[\\/].*/
            ])
        ],
        // Use `--env.stats` to show these stats
        modules: stats,
        entrypoints: stats
    },
    optimization: {
        runtimeChunk: {
            name: 'vendors'
        },
        splitChunks: {
            chunks: 'all',
            maxInitialRequests: Infinity,
            minSize: 0,
            cacheGroups: {
                runtime: {
                    name: 'medusa-runtime',
                    test: /[\\/]src[\\/]/,
                    minChunks: 2,
                    priority: 0,
                    reuseExistingChunk: true
                },
                'date-fns': {
                    name: 'vendors~date-fns',
                    test: /[\\/]node_modules[\\/]date-fns[\\/]/,
                    priority: -5
                },
                vendors: {
                    name: 'vendors',
                    test: /[\\/](vendor|node_modules)[\\/]/,
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
        rules: [
            {
                test: /\.vue$/,
                loader: 'vue-loader',
                options: {
                    // This is a workaround because vue-loader can't get the webpack mode
                    productionMode: isProd
                }
            },
            {
                test: /\.js$/,
                exclude: /[\\/]node_modules[\\/]/,
                loader: 'babel-loader',
                options: {
                    cacheDirectory: !isProd
                }
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
        // Disable other themes' styles in SFCs
        new NormalModuleReplacementPlugin(
            // Match vue SFC styles where the theme name differs from the current theme (`&theme=[name]`)
            new RegExp(String.raw`\?vue&type=style.+&theme=(?!${theme.name})(&|.*$)`),
            'lodash/noop'
        ),
        new OptimizeCssAssetsPlugin({}),
        new MiniCssExtractPlugin({
            filename: 'css/[name].css'
        }),
        // Copy bundled assets for each theme
        // Only use for assets emitted by Webpack.
        new FileManagerPlugin({
            onEnd: {
                copy: [
                    copyAssets(theme, 'js'),
                    copyAssets(theme, 'css'),
                    copyAssets(theme, 'fonts')
                ]
            }
        }),
        // Copy static files for each theme
        // Don't use for assets emitted by Webpack because this plugin runs before the bundle is created.
        new CopyWebpackPlugin([
            // Templates
            {
                context: './views/',
                from: '**',
                to: path.resolve(theme.dest, 'templates')
            },
            // Create package.json
            {
                from: 'package.json',
                to: path.resolve(theme.dest, 'package.json'),
                toType: 'file',
                transform: content => makeThemeMetadata(theme.name, content)
            },
            // Root files: index.html
            {
                from: 'index.html',
                to: path.resolve(theme.dest),
                toType: 'dir'
            },
            // Old JS files
            {
                context: './static/',
                from: 'js/**',
                to: path.resolve(theme.dest, 'assets')
            },
            // Old CSS files
            {
                context: './static/',
                from: 'css/**',
                // Ignore theme-specific files as they are handled by the next entry
                ignore: cssThemes.map(theme => `css/${theme.css}`),
                to: path.resolve(theme.dest, 'assets')
            },
            // Old CSS files - themed.css
            {
                from: `static/css/${theme.css}`,
                to: path.resolve(theme.dest, 'assets', 'css', 'themed.css'),
                toType: 'file'
            }
        ])
    ]
});

/**
 * Generate the Webpack configuration object.
 * @see https://webpack.js.org/configuration/configuration-types/#exporting-a-function
 *
 * @param {object} [env={}] An environment. See the environment options CLI documentation for syntax examples.
 * @param {object} [argv={}] An options map (argv). This describes the options passed to webpack, with keys such as output-filename and optimize-minimize.
 * @returns {object[]} Webpack configurations.
 */
module.exports = (env = {}, argv = {}) => {
    const isProd = (argv.mode || process.env.NODE_ENV) === 'production';
    const stats = Boolean(env.stats);
    const configs = cssThemes.map(theme => makeConfig({ theme, isProd, stats }));
    return configs;
};
