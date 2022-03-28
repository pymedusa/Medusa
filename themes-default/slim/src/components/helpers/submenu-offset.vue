<template>
    <div v-if="$route.meta.subMenu" class="submenu-offset" />
</template>

<script>
export default {
    name: 'submenu-offset'
};
</script>

<style scoped>
    .submenu-offset {
        margin-top: 45px;
    }

    @media (max-width: 991px) and (min-width: 768px) {
        .submenu-offset {
            margin-top: 90px;
        }
    }

    @media (max-width: 991px) {
        .submenu-offset {
            margin-top: 85px;
        }
    }
</style>
