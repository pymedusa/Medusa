<template>
    <component
        :is="linkProperties.is"
        :to="linkProperties.to"
        :href="linkProperties.href"
        :target="linkProperties.target"
        :rel="linkProperties.rel"
        :false-link="linkProperties.falseLink"
        :class="{ 'router-link': linkProperties.is === 'router-link' }"
    >
        <slot></slot>
    </component>
</template>
<script>
import { mapState } from 'vuex';
import router from '../../router';

export default {
    name: 'app-link',
    props: {
        to: [String, Object],
        href: String,
        indexerId: {
            type: String
        },
        placeholder: {
            type: String,
            default: 'indexer-to-name'
        }
    },
    computed: {
        ...mapState(['config']),
        indexerName() {
            const { config, indexerId } = this;
            const { indexers } = config.indexers.config;
            if (!indexerId) {
                return undefined;
            }
            // Returns `undefined` if not found
            return Object.keys(indexers).find(indexer => indexers[indexer].id === parseInt(indexerId, 10));
        },
        computedBase() {
            return document.querySelectorAll('base')[0].getAttribute('href');
        },
        computedHref() {
            const { href, indexerId, placeholder, indexerName } = this;
            if (indexerId && placeholder) {
                return href.replace(placeholder, indexerName);
            }
            return href;
        },
        isIRC() {
            if (!this.computedHref) {
                return;
            }
            return this.computedHref.startsWith('irc://');
        },
        isAbsolute() {
            const href = this.computedHref;
            if (!href) {
                return;
            }
            return /^[a-z][a-z0-9+.-]*:/.test(href);
        },
        isExternal() {
            const base = this.computedBase;
            const href = this.computedHref;
            if (!href) {
                return;
            }
            return !href.startsWith(base) && !href.startsWith('webcal://');
        },
        isHashPath() {
            if (!this.computedHref) {
                return;
            }
            return this.computedHref.startsWith('#');
        },
        anonymisedHref() {
            const { anonRedirect } = this.config;
            const href = this.computedHref;
            if (!href) {
                return;
            }
            return anonRedirect ? anonRedirect + href : href;
        },
        matchingVueRoute() {
            const normalise = str => str ? str.replace(/^\/+|\/+$/g, '') : '';
            return router.options.routes.find(({ path }) => normalise(path) === normalise(this.href));
        },
        linkProperties() {
            const { to, isIRC, isAbsolute, isExternal, isHashPath, anonymisedHref, matchingVueRoute } = this;
            const base = this.computedBase;
            const href = this.computedHref;

            // Return normal router-link
            if (to) {
                return {
                    is: 'router-link',
                    to: (() => {
                        if (typeof to === 'object') {
                            return to;
                        }
                        return {
                            name: to
                        };
                    })()
                };
            }

            // Just return a boring link with other attrs
            // @NOTE: This is for scroll achors as it uses the id
            if (!href) {
                return {
                    is: 'a',
                    // Only tag this as a "false-link" if we passed a name in the props
                    falseLink: Boolean(this.$attrs.name) || undefined
                };
            }

            // If current page and next page are both vue routes return router-link
            if (matchingVueRoute && this.$route && matchingVueRoute.meta.converted && this.$route.meta.converted) {
                // Allows us to skip when we're in a test
                if (window.loadMainApp) {
                    return {
                        is: 'router-link',
                        to: {
                            name: matchingVueRoute.name
                        }
                    };
                }
            }

            return {
                is: 'a',
                target: isAbsolute && isExternal ? '_blank' : '_self',
                href: (() => {
                    if (isHashPath) {
                        const { location } = window;
                        if (location.hash.length === 0) {
                            // Current location might be `url#`
                            const newHash = location.href.endsWith('#') ? href.substr(1) : href;
                            return location.href + newHash;
                        }
                        return location.href.replace(location.hash, '') + href;
                    }
                    if (isIRC) {
                        return href;
                    }
                    if (isAbsolute) {
                        if (isExternal) {
                            return anonymisedHref;
                        }
                        return href;
                    }
                    return new URL(href, base).href;
                })(),
                rel: isAbsolute && isExternal ? 'noreferrer' : undefined
            };
        }
    }
};
</script>
<style>
/*
@NOTE: This fixes the header blocking elements when using a hash link
e.g. displayShow?indexername=tvdb&seriesid=83462#season-5
*/
[false-link]::before {
    content: '';
    display: block;
    position: absolute;
    height: 100px;
    margin-top: -100px;
    z-index: -100;
}

.router-link,
.router-link-active {
    cursor: pointer;
}
</style>
