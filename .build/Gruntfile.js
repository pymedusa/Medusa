module.exports = function(grunt) { // eslint-disable-line xo/filename-case
    require('load-grunt-tasks')(grunt);

    grunt.initConfig({
        clean: {
            dist: './dist/',
            bower_components: './bower_components', // eslint-disable-line camelcase
            fonts: '../static/css/*.ttf',
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
                ],
                dependencies: {
                },
                mainFiles: {
                    'tablesorter': [
                        'dist/js/jquery.tablesorter.combined.js',
                        'dist/js/widgets/widget-columnSelector.min.js',
                        'dist/js/widgets/widget-stickyHeaders.min.js',
                        'dist/css/theme.blue.min.css'
                    ],
                    'bootstrap': [
                        'dist/css/bootstrap.min.css',
                        'dist/js/bootstrap.min.js'
                    ],
                    'bootstrap-formhelpers': [
                        'dist/js/bootstrap-formhelpers.min.js'
                    ],
                    'isotope': [
                        'dist/isotope.pkgd.min.js'
                    ],
                    'outlayer': [
                        'item.js',
                        'outlayer.js'
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
                    dest: '../static/css/'
                }]
            },
            glyphicon: {
                files: [{
                    expand: true,
                    dot: true,
                    cwd: 'bower_components/bootstrap/fonts',
                    src: [
                        '*.eot',
                        '*.svg',
                        '*.ttf',
                        '*.woff',
                        '*.woff2'
                    ],
                    dest: '../static/fonts/'
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
                    dest: '../static/js/',
                    rename: function(dest, src) {
                        return dest + src.replace('bower.js', 'vender.js');
                    }
                }]
            }
        },
        uglify: {
            bower: {
                files: {
                    '../static/js/vender.min.js': './dist/bower.js'
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
                    '../static/css/vender.min.css': './dist/bower.css'
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
