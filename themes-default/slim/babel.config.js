/* eslint comma-dangle: [error, always-multiline] */
const presets = [
    ['@babel/preset-env', {
        targets: {
            browsers: [
                'last 2 Chrome versions',
                'last 2 Firefox versions',
                'last 2 Safari versions',
                'last 1 Edge version',
                'Firefox ESR',
                'last 1 ChromeAndroid version',
                'last 1 FirefoxAndroid version',
                'last 1 iOS version',
            ],
        },
    }],
];

const plugins = [
    '@babel/plugin-transform-runtime',
];

module.exports = {
    presets,
    plugins,
};
