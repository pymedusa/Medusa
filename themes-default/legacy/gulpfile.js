#!/usr/bin/env node
const gutil = require('gulp-util');
const babelify = require('babelify');
const runSequence = require('run-sequence');
const livereload = require('gulp-livereload');
const sourcemaps = require('gulp-sourcemaps');
const gulpif = require('gulp-if');
const xo = require('gulp-xo');
const gulp = require('gulp');
const source = require('vinyl-source-stream');
const uglify = require('gulp-uglify-es').default;
const browserify = require('browserify');
const buffer = require('vinyl-buffer');
const glob = require('glob');
const es = require('event-stream');
const imagemin = require('gulp-imagemin');
const pngquant = require('imagemin-pngquant');
const argv = require('yargs').argv;
const rename = require('gulp-rename');

// Const postcss = require('gulp-postcss');
// const sass = require('gulp-sass');
const cssnano = require('cssnano');
const autoprefixer = require('autoprefixer');
const reporter = require('postcss-reporter');

const PROD = process.env.NODE_ENV === 'production';
const config = require('./package.json').config;

let cssTheme = argv.csstheme;
let buildDest = '';

const processors = [
    reporter({
        clearMessages: true
    }),
    autoprefixer()
];

if (PROD) {
    processors.push(cssnano());
}

const staticAssets = [
    'static/browserconfig.xml',
    'static/favicon.ico',
    'static/fonts/**/*',
    'static/js/**/*',
    'static/css/**/*'
];

/**
 * Get theme object.
 * @param {*} theme name passed by yargs.
 */
const getCssTheme = theme => {
    // Using the --csstheme is mandatory.
    if (argv.csstheme === undefined) {
        console.log('You need to pass a csstheme to build with the param --csstheme');
        process.exit(1);
    }

    // Check if the theme provided is available in the package.json config.
    if (!config.cssThemes[theme]) {
        console.log(`Please provide a valid theme with the --cssTheme parameter, theme ${theme} is not available in the package.json config section.`);
        process.exit(1);
    }
    return config.cssThemes[theme];
};

/**
 * Attemt to get the cssTheme config object from the package.json.
 */
const setCsstheme = () => {
    cssTheme = getCssTheme(cssTheme);
    if (cssTheme) {
        buildDest = cssTheme.dest;
    }
};

const watch = () => {
    livereload.listen({ port: 35729 });
    gulp.watch('static/img/**/*', ['img']);
    gulp.watch('static/css/**/*.scss', ['css']);
    gulp.watch([
        'static/js/**/*.js',
        '!static/js/lib/**',
        '!static/js/*.min.js',
        '!static/js/vender.js'
    ], ['js']);
};

const lint = () => {
    return gulp
        .src([
            'static/js/**/*.js',
            '!static/js/lib/**',
            '!static/js/*.min.js',
            '!static/js/vender.js'
        ])
        .pipe(xo())
        .pipe(xo.format())
        .pipe(xo.failAfterError());
};

const bundleJs = done => {
    glob('js/**/*.js', {
        cwd: 'static',
        ignore: [
            'js/lib/**',
            'js/*.min.js',
            'js/vender.js'
        ]
    }, (err, files) => {
        if (err) {
            return done(err);
        }

        const tasks = files.map(entry => {
            return browserify({
                entries: entry,
                debug: false,
                basedir: 'static'
            })
                .transform(babelify)
                .bundle()
                .on('error', function(err) {
                    gutil.log(err.message);
                    this.emit('end');
                })
                .pipe(source(entry))
                .pipe(buffer())
                .pipe(sourcemaps.init({
                    // Loads map from browserify file
                    loadMaps: true
                }))
                .pipe(gulpif(PROD, uglify()))
                .on('error', err => gutil.log(gutil.colors.red('[Error]'), err.toString()))
                .pipe(sourcemaps.write('./'))
                .pipe(gulp.dest(`${buildDest}/assets`))
                .pipe(gulpif(!PROD, livereload({ port: 35729 })));
        });

        const taskStream = es.merge(tasks);

        taskStream.on('end', done);
    });
};

const moveStatic = () => {
    return gulp
        .src(staticAssets, {
            base: 'static'
        })
        .pipe(gulp.dest(`${buildDest}/assets`));
};

const moveTemplates = () => {
    return gulp
        .src('./views/**/*', {
            base: 'views'
        })
        .pipe(gulp.dest(`${buildDest}/templates`));
};

/**
 * Files from the source root to copy to destination.
 */
const rootFiles = [
    'index.html',
    'package.json'
];

const moveRoot = () => {
    return gulp
        .src(rootFiles)
        .pipe(gulp.dest(buildDest));
};

const moveImages = () => {
    return gulp
        .src('static/images/**/*', {
            base: 'static/images/'
        })
        .pipe(imagemin({
            progressive: true,
            svgoPlugins: [{ removeViewBox: false }, { cleanupIDs: false }],
            use: [pngquant()]
        }))
        .pipe(gulp.dest(`${buildDest}/assets/img`))
        .pipe(gulpif(!PROD, livereload({ port: 35729 })))
        .pipe(gulpif(PROD, gulp.dest(`${buildDest}/assets/img`)));
};

/**
 * Move and rename css.
 */
const moveCss = () => {
    return gulp
        .src(['!static/css/light.css', '!static/css/dark.css', 'static/css/**/*.css'], {
            base: 'static'
        })
        .pipe(gulp.dest(`${buildDest}/assets`));
};

/**
 * Move and rename themed css.
 */
const moveAndRenameCss = () => {
    return gulp
        .src(`static/css/${cssTheme.css}`)
        .pipe(rename(`themed.css`))
        .pipe(gulp.dest(`${buildDest}/assets/css`));
};

/** Gulp tasks */

gulp.task('default', ['build']);

/**
 * Build the current theme and copy all files to the location configured in the package.json config attribute.
 * It's required to pass the theme name through the `--csstheme` parameter.
 * For example: gulp build --csstheme light, will build the theme and rename the light.css to themed.css and
 * copy all files to /themes/[theme dest]/. Themes destination is configured in the package.json.
 */
gulp.task('build', done => {
    // Whe're building the light and dark theme. For this we need to run two sequences.
    // If we need a yargs parameter name csstheme.
    setCsstheme();
    runSequence('lint', ['css', 'cssTheme', 'img', 'js', 'static', 'templates', 'root'], async() => {
        if (!PROD) {
            done();
        }
    });
});

/**
 * Watch file changes and build.
 */
gulp.task('watch', ['build'], watch);

/**
 * Task for compressing and copying images to it's destination. 
 * Should save up to 50% of total filesize.
 */
gulp.task('img', moveImages);

/**
 * Copy all css files to the destination excluding the theme files, as whe're going to rename those.
 */
gulp.task('css', moveCss);

/**
 * Copy and rename the light or dark theme files from the configuration located in the package.json.
 * For example cssThemes.light.css for the `light.css` theme.
 */
gulp.task('cssTheme', moveAndRenameCss);

/**
 * Task for linting the js files using xo.
 * https://github.com/sindresorhus/xo
 */
gulp.task('lint', lint);

/**
 * Task for bundling and copying the js files.
 */
gulp.task('js', bundleJs);

/**
 * Task for moving the static files to the destinations assets directory.
 */
gulp.task('static', moveStatic);

/**
 * Task for moving the mako views to the destinations templates directory.
 */
gulp.task('templates', moveTemplates);

/**
 * Task for moving the files out of the root folder (index.html and package.json) to the destinations
 * root folder. These are required to let medusa read the themes metadata.
 */
gulp.task('root', moveRoot);
