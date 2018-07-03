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
const changed = require('gulp-changed');

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
    if (argv.csstheme === undefined && !theme) {
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
const setCsstheme = theme => {
    cssTheme = getCssTheme(theme || cssTheme);
    if (cssTheme) {
        buildDest = cssTheme.dest;
    }
};

/**
 * Run a single js file through the xo linter. The lintFile function is triggered by a gulp.onChange event.
 * @param {*} file object that has been changed.
 */
const lintFile = file => {
    return gulp
        .src(file.path)
        .pipe(xo())
        .pipe(xo.format());
};

/**
 * Run all js files through the xo (eslint) linter.
 */
const lint = () => {
    return gulp
        .src([
            'static/js/**/*.{js,vue}',
            '!static/js/lib/**',
            '!static/js/*.min.js',
            '!static/js/vender.js'
        ])
        .pipe(xo())
        .pipe(xo.result(result => {
            // Called for each xo result.
            console.log(`xo linting: ${result.filePath}`);
        }))
        .pipe(xo.format(err => {
            // This somehow prints the full path, instead of the relative.
            console.log(err);
        }))
        .pipe(xo.failAfterError());
};

const watch = () => {
    livereload.listen({ port: 35729 });
    // Image changes
    gulp.watch([
        'static/images/**/*.gif',
        'static/images/**/*.png',
        'static/images/**/*.jpg'
    ], ['img']);

    // Css changes
    gulp.watch([
        'static/css/**/*.scss',
        'static/css/**/*.css'
    ], ['css']);

    // Js Changes
    gulp.watch([
        'static/js/**/*.{js,vue}',
        '!static/js/lib/**',
        '!static/js/*.min.js',
        '!static/js/vender.js'
    ], ['js'])
        .on('change', lintFile);

    // Template changes
    gulp.watch('views/**/*.mako', ['templates']);
};

const bundleJs = done => {
    const dest = `${buildDest}/assets`;
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
                .pipe(gulp.dest(dest))
                .pipe(gulpif(!PROD, livereload({ port: 35729 })));
        });

        const taskStream = es.merge(tasks);

        taskStream.on('end', done);
    });
};

const moveStatic = () => {
    const dest = `${buildDest}/assets`;
    return gulp
        .src(staticAssets, {
            base: 'static'
        })
        .pipe(changed(buildDest))
        .pipe(gulp.dest(dest));
};

const moveTemplates = () => {
    const dest = `${buildDest}/templates`;
    return gulp
        .src('./views/**/*', {
            base: 'views'
        })
        .pipe(changed(buildDest))
        .pipe(gulp.dest(dest));
};

/**
 * Files from the source root to copy to destination.
 */
const rootFiles = [
    'index.html',
    'package.json'
];

const moveRoot = () => {
    console.log(`Moving root files to: ${buildDest}`);
    return gulp
        .src(rootFiles)
        .pipe(changed(buildDest))
        .pipe(gulp.dest(buildDest));
};

const moveImages = () => {
    const dest = `${buildDest}/assets/img`;
    return gulp
        .src('static/images/**/*', {
            base: 'static/images/'
        })
        .pipe(changed(dest))
        .pipe(imagemin({
            progressive: true,
            svgoPlugins: [{ removeViewBox: false }, { cleanupIDs: false }],
            use: [pngquant()]
        }))
        .pipe(gulp.dest(dest))
        .pipe(gulpif(!PROD, livereload({ port: 35729 })))
        .pipe(gulpif(PROD, gulp.dest(dest)));
};

/**
 * Move and rename css.
 */
const moveCss = () => {
    const dest = `${buildDest}/assets`;
    return gulp
        .src(['!static/css/light.css', '!static/css/dark.css', 'static/css/**/*.css'], {
            base: 'static'
        })
        .pipe(changed(dest))
        .pipe(gulp.dest(dest));
};

/**
 * Move and rename themed css.
 */
const moveAndRenameCss = () => {
    const dest = `${buildDest}/assets/css`;
    return gulp
        .src(`static/css/${cssTheme.css}`)
        .pipe(rename(`themed.css`))
        .pipe(gulp.dest(dest));
};

/** Gulp tasks */

/**
 * By default build.
 */
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
    runSequence('lint', 'css', 'cssTheme', 'img', 'js', 'static', 'templates', 'root', async() => {
        if (!PROD) {
            done();
        }
    });
});

const syncTheme = (theme, sequence) => {
    return new Promise(resolve => {
        console.log(`Starting syncing for theme: ${theme[0]}`);
        setCsstheme(theme[0]);
        runSequence(sequence, resolve);
    });
};

/**
 * Build the current theme and copy all files to the location configured in the package.json config attribute.
 * It's required to pass the theme name through the `--csstheme` parameter.
 * For example: gulp build --csstheme light, will build the theme and rename the light.css to themed.css and
 * copy all files to /themes/[theme dest]/. Themes destination is configured in the package.json.
 *
 * Do not run the xo build, as this takes a lot of time.
 */
gulp.task('sync', async() => {
    // Whe're building the light and dark theme. For this we need to run two sequences.
    // If we need a yargs parameter name csstheme.
    for (let theme of Object.entries(config.cssThemes)) {
        await syncTheme(theme, ['css', 'cssTheme', 'img', 'js', 'static', 'templates', 'root']);
    }
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
