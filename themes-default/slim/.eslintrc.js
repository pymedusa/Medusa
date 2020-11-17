/* eslint comma-dangle: [error, always-multiline] */
module.exports = {
    parserOptions: {
        ecmaVersion: 2019,
        parser: '@babel/eslint-parser',
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
        'plugin:eslint-comments/recommended',
    ],
    env: {
        browser: true,
        es6: true,
        jquery: true,
    },
    plugins: [
        'unicorn',
        'import',
        'vue',
        '@sharkykh/vue-extra',
        'jest',
        'eslint-comments',
    ],
    settings: {
        'import/resolver': 'webpack',
    },
    rules: {
        indent: [
            'error',
            4,
            {
                SwitchCase: 1,
            },
        ],
        quotes: [
            'error',
            'single',
            {
                avoidEscape: true,
            },
        ],
        'object-curly-spacing': [
            'error',
            'always',
        ],
        'space-before-function-paren': [
            'error',
            {
                anonymous: 'never',
                named: 'never',
                asyncArrow: 'always',
            },
        ],
        'require-await': 'error',
        'valid-jsdoc': 'error',
        'padding-line-between-statements': 'off',
        'unicorn/prevent-abbreviations': 'off',
        'unicorn/no-null': 'off',
        'unicorn/no-useless-undefined': 'off',
        'unicorn/no-reduce': 'off',
        'unicorn/consistent-function-scoping': 'off',
        'unicorn/prefer-optional-catch-binding': 'off',
        'unicorn/no-fn-reference-in-iterator': 'off',
        'vue/html-indent': [
            'error',
            4,
        ],
        'vue/html-quotes': [
            'error',
            'double',
        ],
        'vue/name-property-casing': [
            'error',
            'kebab-case',
        ],
        'vue/html-self-closing': 'error',
        'vue/html-closing-bracket-spacing': [
            'error',
            {
                selfClosingTag: 'always',
            },
        ],
    },
    // Please do not use root `globals` because they can't be overriden.
    globals: {},
    overrides: [
        {
            files: 'static/js/**',
            rules: {
                'unicorn/prefer-includes': 'off',
                'unicorn/prefer-text-content': 'off',
            },
            globals: {
                PNotify: 'readonly',
                LazyLoad: 'readonly',
                _: 'readonly',
                MEDUSA: 'readonly',
                api: 'readonly',
                apiv1: 'readonly',
                apiRoute: 'readonly',
                axios: 'readonly',
                webRoot: 'readonly',
                apiKey: 'readonly',
                Vuex: 'readonly',
            },
        },
        {
            files: 'src/**',
            rules: {
                '@sharkykh/vue-extra/component-not-registered': [
                    'error',
                    [
                        'router-link',
                        'router-view',
                        'vue-snotify',
                    ],
                ],
                'import/extensions': [
                    'error',
                    'always',
                    {
                        js: 'ignorePackages',
                        vue: 'ignorePackages',
                        json: 'ignorePackages',
                    },
                ],
            },
            globals: {
                MEDUSA: 'readonly',
            },
        },
    ],
};
