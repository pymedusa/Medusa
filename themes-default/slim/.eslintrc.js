module.exports = {
    parserOptions: {
        ecmaVersion: 2019,
        parser: 'babel-eslint',
        sourceType: 'module',
        allowImportExportEverywhere: false,
        codeFrame: true,
    },
    extends: [
        'xo',
        'xo/esnext',
        'plugin:unicorn/recommended',
        'plugin:import/errors',
        'plugin:import/warnings',
        'plugin:vue/essential',
        'plugin:jest/recommended',
        'plugin:eslint-comments/recommended'
    ],
    env: {
        browser: true,
        es6: true,
        jquery: true
    },
    plugins: [
        'unicorn',
        'import',
        'vue',
        'jest',
        'eslint-comments'
    ],
    settings: {
        'import/resolver': 'webpack'
    },
    rules: {
        indent: [
            'error',
            4,
            {
                SwitchCase: 1
            }
        ],
        quotes: [
            'error',
            'single',
            {
                avoidEscape: true
            }
        ],
        'object-curly-spacing': [
            'error',
            'always'
        ],
        'space-before-function-paren': [
            'error',
            {
                'anonymous': 'never',
                'named': 'never',
                'asyncArrow': 'always'
            }
        ],
        'valid-jsdoc': [
            'error'
        ],
        'padding-line-between-statements': 'off',
        'unicorn/prevent-abbreviations': 'off',
    },
    // Please do not use root `globals` because they can't be overriden.
    globals: {},
    overrides: [
        {
            files: "static/js/**",
            rules: {
                'unicorn/prefer-includes': 'off',
                'unicorn/prefer-text-content': 'off'
            },
            globals: {
                'PNotify': 'readonly',
                'LazyLoad': 'readonly',
                '_': 'readonly',
                'MEDUSA': 'readonly',
                'api': 'readonly',
                'apiv1': 'readonly',
                'apiRoute': 'readonly',
                'axios': 'readonly',
                'webRoot': 'readonly',
                'apiKey': 'readonly',
                'Vuex': 'readonly',
            }
        },
        {
            files: "src/**",
            rules: {
                'import/extensions': [
                    'error',
                    'always',
                    {
                        js: 'ignorePackages',
                        vue: 'ignorePackages',
                        json: 'ignorePackages',
                    }
                ],
            },
            globals: {
                'MEDUSA': 'readonly',
            },
        }
    ],
};
