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
        <slot />
    </component>
</template>
<script>
import { mapGetters, mapState } from 'vuex';

import router, { base as routerBase } from '../../router';

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
        ...mapState({
            general: state => state.config.general
        }),
        ...mapGetters(['indexerIdToName']),
        indexerName() {
            // Returns `undefined` if not found
            const { indexerId, indexerIdToName } = this;
            return indexerIdToName(indexerId);
        },
        computedBase() {
            return document.querySelector('base').getAttribute('href');
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
            return /^[a-z][\d+.a-z-]*:/.test(href);
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
            const { anonRedirect } = this.general;
            const href = this.computedHref;
            if (!href) {
                return;
            }
            return anonRedirect ? anonRedirect + href : href;
        },
        matchingVueRoute() {
            const { isAbsolute, isExternal, computedHref } = this;
            if (isAbsolute && isExternal) {
                return;
            }

            const { route } = router.resolve(routerBase + computedHref);
            if (!route.name) {
                return;
            }

            return route;
        },
        linkProperties() {
            const { to, isIRC, isAbsolute, isExternal, isHashPath, anonymisedHref, matchingVueRoute } = this;
            const base = this.computedBase;
            const href = this.computedHref;

            // Return normal router-link
            if (to) {
                return {
                    is: 'router-link',
                    to
                };
            }

            // Just return a boring link with other attrs
            // @NOTE: This is for scroll anchors as it uses the id
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
                        to: matchingVueRoute.fullPath,
                        // Add a `href` attribute to enable native mouse navigation (middle click, ctrl+click, etc.)
                        href: new URL(matchingVueRoute.fullPath, base).href
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
                            const newHash = location.href.endsWith('#') ? href.slice(1) : href;
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
