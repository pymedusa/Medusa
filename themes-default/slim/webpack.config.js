const path = require('path');
const VueLoaderPlugin = require('vue-loader/lib/plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = {
    devtool: 'eval',
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
    plugins: [
        new VueLoaderPlugin(),
        new CopyWebpackPlugin([{
            from: path.resolve(__dirname, 'dist', 'js'),
            to: path.resolve(__dirname, '../../themes/dark/assets/js/')
        }, {
            from: path.resolve(__dirname, 'dist', 'js'),
            to: path.resolve(__dirname, '../../themes/light/assets/js/')
        }])
    ]
};
