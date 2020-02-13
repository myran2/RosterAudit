-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Server version:               10.4.11-MariaDB - mariadb.org binary distribution
-- Server OS:                    Win64
-- HeidiSQL Version:             10.3.0.5771
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;

-- Dumping structure for table rosteraudit.raider
CREATE TABLE IF NOT EXISTS `raider` (
  `blizz_id` bigint(20) unsigned NOT NULL,
  `name` tinytext NOT NULL,
  `playerClass` tinyint(3) unsigned NOT NULL,
  `playerRoles` tinyint(3) unsigned NOT NULL,
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

-- Dumping structure for table rosteraudit.raider_history
CREATE TABLE IF NOT EXISTS `raider_history` (
  `raider_id` bigint(20) unsigned NOT NULL,
  `neck_level` double unsigned NOT NULL,
  `cape_level` bigint(20) unsigned NOT NULL,
  `timestamp` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`raider_id`,`timestamp`),
  CONSTRAINT `FK_raider_history_raider` FOREIGN KEY (`raider_id`) REFERENCES `raider` (`blizz_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.

-- Dumping structure for table rosteraudit.raider_key_history
CREATE TABLE IF NOT EXISTS `raider_key_history` (
  `raider_id` bigint(20) unsigned NOT NULL,
  `key_level` tinyint(3) unsigned NOT NULL,
  `dungeon` smallint(5) unsigned NOT NULL,
  `timestamp` datetime NOT NULL,
  PRIMARY KEY (`timestamp`,`raider_id`),
  KEY `FK_raider_key_history_raider` (`raider_id`),
  CONSTRAINT `FK_raider_key_history_raider` FOREIGN KEY (`raider_id`) REFERENCES `raider` (`blizz_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.

/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IF(@OLD_FOREIGN_KEY_CHECKS IS NULL, 1, @OLD_FOREIGN_KEY_CHECKS) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
