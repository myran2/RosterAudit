-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Server version:               10.4.11-MariaDB - mariadb.org binary distribution
-- Server OS:                    Win64
-- HeidiSQL Version:             11.3.0.6295
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

-- Dumping structure for table rosteraudit.raider
CREATE TABLE IF NOT EXISTS `raider` (
  `blizz_id` bigint(20) unsigned NOT NULL,
  `name` tinytext NOT NULL,
  `playerClass` tinyint(3) unsigned NOT NULL,
  `playerRoles` tinyint(3) unsigned NOT NULL DEFAULT 0,
  `ignore` tinyint(4) NOT NULL DEFAULT 0,
  `realm` tinytext NOT NULL DEFAULT 'bleeding-hollow',
  PRIMARY KEY (`blizz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.

-- Dumping structure for table rosteraudit.raider_alts
CREATE TABLE IF NOT EXISTS `raider_alts` (
  `raider_id` bigint(20) unsigned NOT NULL,
  `raider_main_id` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`raider_id`,`raider_main_id`),
  KEY `FK_raider_alts_raider_2` (`raider_main_id`),
  CONSTRAINT `FK_raider_alts_raider` FOREIGN KEY (`raider_id`) REFERENCES `raider` (`blizz_id`) ON DELETE CASCADE,
  CONSTRAINT `FK_raider_alts_raider_2` FOREIGN KEY (`raider_main_id`) REFERENCES `raider` (`blizz_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.

-- Dumping structure for table rosteraudit.raider_boss_history
CREATE TABLE IF NOT EXISTS `raider_boss_history` (
  `raider_id` bigint(20) unsigned NOT NULL,
  `raid_difficulty` tinyint(3) unsigned NOT NULL,
  `boss_kill_count` tinyint(3) unsigned NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT utc_timestamp(),
  PRIMARY KEY (`raider_id`,`timestamp`),
  CONSTRAINT `FK_raider_history_raider` FOREIGN KEY (`raider_id`) REFERENCES `raider` (`blizz_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.

-- Dumping structure for table rosteraudit.raider_key_history
CREATE TABLE IF NOT EXISTS `raider_key_history` (
  `raider_id` bigint(20) unsigned NOT NULL,
  `key_level` tinyint(3) unsigned NOT NULL,
  `dungeon` smallint(5) unsigned NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT utc_timestamp(),
  PRIMARY KEY (`timestamp`,`raider_id`,`dungeon`) USING BTREE,
  KEY `FK_raider_key_history_raider` (`raider_id`),
  CONSTRAINT `FK_raider_key_history_raider` FOREIGN KEY (`raider_id`) REFERENCES `raider` (`blizz_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.

-- Dumping structure for table rosteraudit.raider_pvp_history
CREATE TABLE IF NOT EXISTS `raider_pvp_history` (
  `raider_id` bigint(20) unsigned NOT NULL,
  `bracket` tinyint(3) unsigned NOT NULL,
  `win_count` smallint(5) unsigned NOT NULL,
  `loss_count` smallint(5) unsigned NOT NULL,
  `rating` smallint(6) NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT utc_timestamp(),
  PRIMARY KEY (`timestamp`,`raider_id`,`bracket`) USING BTREE,
  KEY `FK_raider_pvp_history_raider` (`raider_id`) USING BTREE,
  CONSTRAINT `FK_raider_pvp_history_raider` FOREIGN KEY (`raider_id`) REFERENCES `raider` (`blizz_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.

/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
