const path = require('path');

module.exports = {
    mode: process.env.NODE_ENV || 'production',
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
    }
};
