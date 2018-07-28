const path = require('path');
const VueLoaderPlugin = require('vue-loader/lib/plugin');
const FileManagerPlugin = require('filemanager-webpack-plugin');

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
            onEnd: {
                copy: [{
                    source: './dist/js/**', destination: '../../themes/dark/assets/js/'
                }, {
                    source: './dist/js/**', destination: '../../themes/light/assets/js/'
                }]
            }
        })
    ]
};
