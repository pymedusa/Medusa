<template>
    <li :class="open ? 'active' : ''" class="navbar-split dropdown">
        <a @click="toggleDropdown" @mouseenter="toggleDropdown" :title="title" class="dropdown-toggle">
            <template v-if="icon"><img :src="icon" class="navbaricon hidden-xs" /> <b class="caret"></b></template>
            <template v-else>{{title}} <b class="caret"></b></template>
        </a>
        <ul @mouseleave="toggleDropdown" class="dropdown-menu">
            <slot></slot>
        </ul>
        <div style="clear:both;"></div>
    </li>
</template>

<script>
export default {
    name: 'dropdown',
    data() {
        return {
            open: false,
            timeout: null
        };
    },
    props: {
        title: String,
        icon: String,
        badge: Number
    },
    methods: {
        toggleDropdown() {
            const vm = this;
            vm.open = !vm.open;
            clearTimeout(vm.timeout);
            vm.timeout = setTimeout(() => {
                vm.open = false;
            }, 2000);
        }
    }
};
</script>

<style>
.dropdown.active ul.dropdown-menu {
    display: block;
}
</style>
