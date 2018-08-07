module.exports = function(grunt) { // eslint-disable-line xo/filename-case
    require('load-grunt-tasks')(grunt);

    grunt.initConfig({
        clean: {
            dist: './dist/',
            bower_components: './bower_components', // eslint-disable-line camelcase
            fonts: '../themes-default/slim/static/css/*.ttf',
            options: {
                force: true
            }
        },
        bower: {
            install: {
                options: {
                    copy: false
                }
            }
        },
        bower_concat: { // eslint-disable-line camelcase
            all: {
                dest: {
                    js: './dist/bower.js',
                    css: './dist/bower.css'
                },
                exclude: [
                    // Moved to Webpack
                    'jquery',
                    'bootstrap'
                ],
                dependencies: {
                },
                mainFiles: {
                    tablesorter: [
                        'dist/js/jquery.tablesorter.combined.js',
                        'dist/js/widgets/widget-columnSelector.min.js',
                        'dist/css/theme.blue.min.css'
                    ],
                    isotope: [
                        'dist/isotope.pkgd.min.js'
                    ],
                    outlayer: [
                        'item.js',
                        'outlayer.js'
                    ],
                    openSans: [
                        'openSans.css'
                    ]
                },
                bowerOptions: {
                    relative: false
                }
            }
        },
        copy: {
            openSans: {
                files: [{
                    expand: true,
                    dot: true,
                    cwd: 'bower_components/openSans',
                    src: [
                        '*.ttf'
                    ],
                    dest: '../themes-default/slim/static/css/'
                }]
            },
            vender: {
                files: [{
                    expand: true,
                    dot: true,
                    cwd: 'dist',
                    src: [
                        'bower.js'
                    ],
                    dest: '../themes-default/slim/static/js/',
                    rename: function(dest, src) {
                        return dest + src.replace('bower.js', 'vender.js');
                    }
                }]
            }
        },
        uglify: {
            bower: {
                files: {
                    '../themes-default/slim/static/js/vender.min.js': './dist/bower.js'
                }
            }
        },
        cssmin: {
            options: {
                shorthandCompacting: false,
                roundingPrecision: -1
            },
            bower: {
                files: {
                    '../themes-default/slim/static/css/vender.min.css': './dist/bower.css'
                }
            }
        }
    });

    grunt.loadNpmTasks('grunt-contrib-clean');
    grunt.loadNpmTasks('grunt-bower-task');
    grunt.loadNpmTasks('grunt-bower-concat');
    grunt.loadNpmTasks('grunt-contrib-copy');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-contrib-cssmin');

    grunt.registerTask('default', [
        'clean',
        'bower',
        'bower_concat',
        'copy',
        'uglify',
        'cssmin'
    ]);
};
