const path = require('path');
const { ProvidePlugin } = require('webpack');
const VueLoaderPlugin = require('vue-loader/lib/plugin');
const FileManagerPlugin = require('filemanager-webpack-plugin');
const pkg = require('./package.json');

const { config } = pkg;
const { cssThemes } = config;

const webpackConfig = mode => ({
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
    optimization: {
        runtimeChunk: {
            name: 'vendors'
        },
        splitChunks: {
            chunks: 'all',
            name: 'vendors',
            cacheGroups: {
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
                        productionMode: mode === 'production',
                        loaders: {
                            css: ['vue-style-loader', { loader: 'css-loader' }],
                            js: ['babel-loader']
                        }
                    }
                }]
            },
            {
                test: /\.js$/,
                loader: 'babel-loader'
            },
            {
                test: /\.css$/,
                use: [
                    {
                        loader: 'style-loader',
                        options: {
                            insertAt: 'top'
                        }
                    },
                    'css-loader'
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
        new FileManagerPlugin({
            onEnd: {
                copy: Object.values(cssThemes).reduce((operations, theme) => {
                    // Queue operations for each theme
                    operations.push({
                        source: './dist/js/**',
                        destination: path.join(theme.dest, 'assets', 'js')
                    });
                    operations.push({
                        source: './dist/fonts/**',
                        destination: path.join(theme.dest, 'assets', 'fonts')
                    });
                    return operations;
                }, [])
            }
        })
    ]
});

module.exports = (_env, argv) => webpackConfig(argv.mode);
