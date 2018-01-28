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

const rootFiles = [
    'index.html',
    'package.json'
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
cssTheme = getCssTheme(cssTheme);
if (cssTheme) {
    buildDest = cssTheme.dest;
}

gulp.task('default', ['build']);

gulp.task('build', done => {
    // Whe're building the light and dark theme. For this we need to run two sequences.
    // If we need a yargs parameter name csstheme.
    
    runSequence('lint', ['css', 'cssTheme', 'img', 'js', 'static', 'templates', 'vue', 'root'], async () => {
        if (!PROD) {
            done();
        }
    });
});

gulp.task('watch', ['build'], () => {
    livereload.listen({ port: 35729 });
    gulp.watch('static/img/**/*', ['img']);
    gulp.watch('static/css/**/*.scss', ['css']);
    gulp.watch([
        'static/js/**/*.js',
        '!static/js/lib/**',
        '!static/js/*.min.js',
        '!static/js/vender.js'
    ], ['js']);
});

gulp.task('img', () => {
    return gulp
    .src('static/images/**/*', {
        base: 'static/images/'
    })
    .pipe(
      imagemin({
          progressive: true,
          svgoPlugins: [{ removeViewBox: false }, { cleanupIDs: false }],
          use: [pngquant()]
      })
    )
    .pipe(gulp.dest(`${buildDest}/assets/img`))
    .pipe(gulpif(!PROD, livereload({ port: 35729 })))
    .pipe(gulpif(PROD, gulp.dest(`${buildDest}/assets/img`)));
});

gulp.task('css', () => {
    return gulp
    .src(['!static/css/light.css', '!static/css/dark.css', 'static/css/**/*.css'], {
        base: 'static'
    })
    // .pipe(sourcemaps.init())
    // .pipe(sass().on('error', sass.logError))
    // .pipe(postcss(processors))
    // .pipe(sourcemaps.write('./'))
    // .pipe(gulp.dest('build'))
    // .pipe(gulpif(!PROD, livereload({ port: 35729 })))
    .pipe(gulp.dest(`${buildDest}/assets`));
});

gulp.task('cssTheme', () => {
    return gulp
    .src(`static/css/${cssTheme.css}`)
    // .pipe(sourcemaps.init())
    // .pipe(sass().on('error', sass.logError))
    // .pipe(postcss(processors))
    // .pipe(sourcemaps.write('./'))
    // .pipe(gulp.dest('build'))
    // .pipe(gulpif(!PROD, livereload({ port: 35729 })))
    .pipe(rename(`themed.css`))
    .pipe(gulp.dest(`${buildDest}/assets/css`));
});

gulp.task('lint', () => {
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
});

//
// gulp.task('js', ['lint'], done => {
gulp.task('js', done => {
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
          .pipe(
            sourcemaps.init({
                // Loads map from browserify file
                loadMaps: true
            })
          )
          .pipe(gulpif(PROD, uglify()))
          .on('error', err => gutil.log(gutil.colors.red('[Error]'), err.toString()))
          .pipe(sourcemaps.write('./'))
          .pipe(gulp.dest(`${buildDest}/assets`))
          .pipe(gulpif(!PROD, livereload({ port: 35729 })));
        });

        const taskStream = es.merge(tasks);

        taskStream.on('end', done);
    });
});

gulp.task('static', () => {
    return gulp
    .src(staticAssets, {
        base: 'static'
    })
    .pipe(gulp.dest(`${buildDest}/assets`));
});

gulp.task('templates', () => {
    return gulp
    .src('./views/**/*', {
        base: 'views'
    })
    .pipe(gulp.dest(`${buildDest}/templates`));
});

gulp.task('vue', () => {
    return gulp
    .src('./vue/**/*')
    .pipe(gulp.dest(`${buildDest}/vue`));
});

gulp.task('root', () => {
    return gulp
    .src(rootFiles)
    .pipe(gulp.dest(buildDest));
});
