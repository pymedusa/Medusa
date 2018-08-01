const path = require('path');
const VueLoaderPlugin = require('vue-loader/lib/plugin');
const FileManagerPlugin = require('filemanager-webpack-plugin');
const pkg = require('./package.json');

const { config } = pkg;
const { cssThemes } = config;

module.exports = {
    entry: {
        // Exports all window. objects for mako files
        index: './static/js/index.js',
        // Main Vue app
        app: './static/js/app.js'
    },
    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, 'dist', 'js')
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
        splitChunks: {
            chunks: 'all',
            name: 'vendors'
        }
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: 'vue-loader'
            },
            {
                test: /\.js$/,
                loader: 'babel-loader'
            },
            {
                test: /\.css$/,
                use: [
                    'vue-style-loader',
                    'css-loader'
                ]
            }
        ]
    },
    plugins: [
        new VueLoaderPlugin(),
        new FileManagerPlugin({
            onStart: {
                delete: [
                    './dist/js/**'
                ]
            },
            onEnd: {
                copy: Object.values(cssThemes).reduce((operations, theme) => {
                    // Queue operations for each theme
                    operations.push({
                        source: './dist/js/**',
                        destination: path.join(theme.dest, 'assets', 'js')
                    });
                    return operations;
                }, [])
            }
        })
    ]
};
