import * as Util from '../helpers/util';

import React, {Fragment, useState} from 'react'
import {Dialog, Menu, Transition} from '@headlessui/react'
import {
    ArrowLeftOnRectangleIcon,
    Bars3Icon,
    BellIcon,
    BuildingOfficeIcon,
    UserCircleIcon, UsersIcon
} from '@heroicons/react/24/outline'
import {ChevronDownIcon, MagnifyingGlassIcon} from "@heroicons/react/20/solid";
import { useStore } from "../store";
import {useNavigate} from "react-router-dom";


export const HeaderSearch = (props) => {
    const { search, onSidebarOpen, onSearch, showToast } = props

    const usr_info = {
        uid: '',
        name: 'Luke Dupin',
        profile_url: '/static/profile.jpg',
    }

    const navigate = useNavigate()

    const handleSearch = e => {
        onSearch(e.target.value)
    }

    const handleSignout = () => {
        Util.fetch_js('/api/human/logout/', {},
            js => {
                navigate('/login')
            }, showToast)
    }

    const userNavigation = [
        { name: 'Your profile', icon: UserCircleIcon, onClick: () => navigate(`/profile/${usr_info.uid}`) },
        { name: 'Tenant', icon: BuildingOfficeIcon, onClick: () => navigate('/tenant') },
        { name: 'Team', icon: UsersIcon, onClick: () => navigate('/team') },
        { name: 'Sign out', icon: ArrowLeftOnRectangleIcon, onClick: handleSignout },
    ]

    return (
        <header id="site-header"
                className="sticky top-0 z-50 p-1.5 bg-background/80 backdrop-blur-md border-b border-surface">
            <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"
                 aria-label="Main navigation">
                <div
                    className="flex items-center justify-between h-16">
                    <a href="/"
                       className="flex items-center gap-2 font-semibold text-lg text-text">
                        <img src="/static/anchor_logo.png" alt="Mountain America Homes"
                             className="h-8 w-auto"/> Mountain America Homes
                    </a>
                    <div className="hidden md:flex items-center gap-6"><a
                        href="/features"
                        className="text-text-muted hover:text-text transition-colors text-sm font-medium rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background focus:outline-none"> Features </a><a
                        href="/pricing"
                        className="text-text-muted hover:text-text transition-colors text-sm font-medium rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background focus:outline-none"> Pricing </a><a
                        href="/dashboard"
                        className="text-text-muted hover:text-text transition-colors text-sm font-medium rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background focus:outline-none"> Demo </a><a
                        href="/customers"
                        className="text-text-muted hover:text-text transition-colors text-sm font-medium rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background focus:outline-none"> Customers </a><a
                        href="/enterprise"
                        className="text-text-muted hover:text-text transition-colors text-sm font-medium rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background focus:outline-none"> Enterprise </a><a
                        href="/docs"
                        className="text-text-muted hover:text-text transition-colors text-sm font-medium rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background focus:outline-none"> Docs </a><a
                        href="/blog"
                        className="text-text-muted hover:text-text transition-colors text-sm font-medium rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background focus:outline-none"> Blog </a>
                    </div>
                    <div className="hidden md:flex items-center gap-4">
                        <button type="button" aria-label="Toggle dark mode"
                                className="theme-toggle cursor-pointer p-2 rounded-md hover:bg-surface transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background">
                            <svg width="1em" height="1em"
                                 className="sun-icon hidden w-5 h-5 text-text"
                                 data-icon="lucide:sun">
                                <symbol id="ai:lucide:sun" viewBox="0 0 24 24">
                                    <g fill="none" stroke="currentColor"
                                       strokeLinecap="round"
                                       strokeLinejoin="round" strokeWidth="2">
                                        <circle cx="12" cy="12" r="4"></circle>
                                        <path
                                            d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path>
                                    </g>
                                </symbol>
                                <use href="#ai:lucide:sun"></use>
                            </svg>
                            <svg width="1em" height="1em"
                                 className="moon-icon w-5 h-5 text-text"
                                 data-icon="lucide:moon">
                                <symbol id="ai:lucide:moon" viewBox="0 0 24 24">
                                    <path fill="none" stroke="currentColor"
                                          strokeLinecap="round"
                                          strokeLinejoin="round"
                                          strokeWidth="2"
                                          d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401"></path>
                                </symbol>
                                <use href="#ai:lucide:moon"></use>
                            </svg>
                        </button>
                        <script type="module"
                                src="/src/components/ui/ThemeToggle.astro?astro&amp;type=script&amp;index=0&amp;lang.ts"></script>
                        <a href="/login"
                           className="text-text-muted hover:text-text transition-colors text-sm font-medium rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background focus:outline-none"> Login </a>
                        <a href="/register"
                           className="px-4 py-2 w-28 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-primary-dark transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background">
                            Get Started </a>
                    </div>
                    <div className="flex items-center gap-2 md:hidden">
                        <button type="button" aria-label="Toggle dark mode"
                                className="theme-toggle cursor-pointer p-2 rounded-md hover:bg-surface transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background">
                            <svg width="1em" height="1em" viewBox="0 0 24 24"
                                 className="sun-icon hidden w-5 h-5 text-text"
                                 data-icon="lucide:sun">
                                <use href="#ai:lucide:sun"></use>
                            </svg>
                            <svg width="1em" height="1em" viewBox="0 0 24 24"
                                 className="moon-icon w-5 h-5 text-text"
                                 data-icon="lucide:moon">
                                <use href="#ai:lucide:moon"></use>
                            </svg>
                        </button>
                        <button id="mobile-menu-button" type="button"
                                aria-label="Toggle mobile menu"
                                aria-expanded="false"
                                aria-controls="mobile-menu"
                                className="p-2 rounded-md hover:bg-surface transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background">
                            <svg width="1em" height="1em" id="menu-icon-open"
                                 className="w-6 h-6 text-text"
                                 aria-hidden="true" data-icon="lucide:menu">
                                <symbol id="ai:lucide:menu" viewBox="0 0 24 24">
                                    <path fill="none" stroke="currentColor"
                                          strokeLinecap="round"
                                          strokeLinejoin="round"
                                          strokeWidth="2"
                                          d="M4 5h16M4 12h16M4 19h16"></path>
                                </symbol>
                                <use href="#ai:lucide:menu"></use>
                            </svg>
                            <svg width="1em" height="1em" viewBox="0 0 24 24"
                                 id="menu-icon-close"
                                 className="hidden w-6 h-6 text-text"
                                 aria-hidden="true" data-icon="lucide:x">
                                <use href="#ai:lucide:x"></use>
                            </svg>
                        </button>
                    </div>
                </div>
            </nav>
        </header>
    );
}
