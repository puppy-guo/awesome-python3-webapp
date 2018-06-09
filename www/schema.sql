-- schemal.sql

DROP DATABASE IF EXISTS aswsome;

CREATE DATABASE aswsome;

USE aswsome;

GRANT SELECT, INSERT, UPDATE, DELETE ON aswsome.* TO 'www-data'@'localhost' indentified BY 'www-data';

CREATE TABLE users (
    `id` VARCHAR(50) NOT NULL,
    `email` VARCHAR(50) NOT NULL,
    `passwd` VARCHAR(50) NOT NULL,
    `admin` bool not NULL,
    `name` VARCHAR(50) NOT NULL,
    'image' VARCHAR(50) NOT NULL,
    'create_at' REAL NOT NULL,
    UNIQUE KEY `idx_email` (`email`)
    KEY `idx_create_at` (`create_at`)
    PRIMARY KEY (`id`)
)engine=innodb DEFAULT charset=utf-8;

CREATE TABLE blogs (
    `id` VARCHAR(50) NOT NULL,
    
)