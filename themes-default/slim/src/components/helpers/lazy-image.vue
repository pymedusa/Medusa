<template>
    <img :data-src="lazySrc"
         :data-srcset="lazySrcset"
         :class="lazyCls"
         :style="style"
         class="app-image"
         @error="error = true"
    >
</template>

<script>
import lozad from 'lozad';

export default {
    name: 'lazy-image',
    props: {
        height: {
            type: Number,
            default: null
        },
        lazySrc: {
            type: String,
            default: null
        },
        lazySrcset: {
            type: String,
            default: null
        },
        lazyDefaultSrc: {
            type: String,
            default: null
        },
        lazyCls: {
            type: String,
            default: ''
        },
        width: {
            type: Number,
            default: null
        }
    },
    data() {
        return {
            loading: true,
            error: false
        };
    },
    computed: {
        aspectRatio() {
            // Calculate the aspect ratio of the image
            // if the width and the height are given.
            if (!this.width || !this.height) {
                return null;
            }

            return (this.height / this.width) * 100;
        },
        style() {
            const style = {};

            if (this.width) {
                style.width = `${this.width}px`;
            }

            // If the image is still loading and an
            // aspect ratio could be calculated, we
            // apply the calculated aspect ratio by
            // using padding top.
            const applyAspectRatio = this.loading && this.aspectRatio;
            if (applyAspectRatio) {
                // Prevent flash of unstyled image
                // after the image is loaded.
                style.height = 0;
                // Scale the image container according
                // to the aspect ratio.
                style.paddingTop = `${this.aspectRatio}%`;
            }

            return style;
        }
    },
    mounted() {
    // As soon as the <img> element triggers
    // the `load` event, the loading state is
    // set to `false`, which removes the apsect
    // ratio we've applied earlier.
        const setLoadingState = () => {
            this.loading = false;
        };
        this.$el.addEventListener('load', setLoadingState);
        // We remove the event listener as soon as
        // the component is destroyed to prevent
        // potential memory leaks.
        this.$once('hook:destroyed', () => {
            this.$el.removeEventListener('load', setLoadingState);
        });

        // We initialize Lozad.js on the root
        // element of our component.
        const observer = lozad(this.$el, {
            loaded: el => {
                el.classList.add('loaded');

                const img = new Image();
                img.src = el.getAttribute('data-src');
                img.addEventListener('error', () => {
                    el.classList.add('error');
                    if (this.lazyDefaultSrc) {
                        el.setAttribute('src', this.lazyDefaultSrc);
                    }
                }, false);
            }
        });
        observer.observe();
    },
    methods: {
        observe() {
            // We initialize Lozad.js on the root
            // element of our component.
            const observer = lozad(this.$el);
            observer.observe();
        }
    }
};
</script>

<style scoped>
.app-image {
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
    vertical-align: middle;
}

img:not([src]) {
    visibility: hidden;
}
</style>
