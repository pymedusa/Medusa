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
// const postcss = require('gulp-postcss');
// const sass = require('gulp-sass');
const cssnano = require('cssnano');
const autoprefixer = require('autoprefixer');
const reporter = require('postcss-reporter');

const PROD = process.env.NODE_ENV === 'production';

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
    'static/manifest.json',
    'static/fonts/**/*',
    'static/js/lib/**/*',
    'static/js/vender.js',
    'static/js/vender.min.js',
    'static/css/**/*'
];

gulp.task('default', ['build']);

gulp.task('build', done => {
    runSequence('lint', ['css', 'img', 'js', 'static'], async () => {
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
        base: 'static'
    })
    .pipe(
      imagemin({
          progressive: true,
          svgoPlugins: [{ removeViewBox: false }, { cleanupIDs: false }],
          use: [pngquant()]
      })
    )
    .pipe(gulp.dest('build'))
    .pipe(gulpif(!PROD, livereload({ port: 35729 })))
    .pipe(gulpif(PROD, gulp.dest('build')));
});

gulp.task('css', () => {
    //
    // return gulp
    // .src('static/css/**/*.css', {
    //     base: 'static'
    // })
    // .pipe(sourcemaps.init())
    // .pipe(sass().on('error', sass.logError))
    // .pipe(postcss(processors))
    // .pipe(sourcemaps.write('./'))
    // .pipe(gulp.dest('build'))
    // .pipe(gulpif(!PROD, livereload({ port: 35729 })))
    // .pipe(gulpif(PROD, gulp.dest('build')));
    return;
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
          .pipe(gulp.dest('build'))
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
    .pipe(gulp.dest('build'));
});
